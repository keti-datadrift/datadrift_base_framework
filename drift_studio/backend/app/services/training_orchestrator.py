"""Training Orchestrator — sends training commands to trainer agents.

When the DriftDecisionEngine decides RETRAIN, this orchestrator:
1. Looks up the trainer agent
2. Builds a TrainingCommand
3. Sends it via HTTP to the trainer's API
4. Creates a TrainingJob record for tracking
5. Receives results via callback
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models import FieldDriftReport, TrainerAgent, TrainingJob

logger = logging.getLogger(__name__)


class TrainingOrchestrator:
    """Orchestrates training across registered trainer agents."""

    def trigger_training(
        self,
        db: Session,
        *,
        trainer: TrainerAgent,
        drift_report: FieldDriftReport,
        training_params: dict | None = None,
    ) -> TrainingJob:
        """Create and dispatch a training job.

        Returns the TrainingJob record (status=pending initially).
        The actual training runs asynchronously on the trainer agent.
        """
        model_name = drift_report.model_name or "unknown"
        report_json = drift_report.report_json or {}
        diagnosis = report_json.get("diagnosis", {})
        recommendations = diagnosis.get("recommendations", [])

        # Build TrainingCommand
        command = {
            "command_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source_report_id": drift_report.id,
            "field_app_id": drift_report.agent_id,
            "training": {
                "pipeline": trainer.trainer_type or "generic",
                "stage": _infer_stage(model_name),
                "mode": "finetune",
                "params": training_params or _default_params(model_name),
                "acceptance_criteria": {
                    "min_accuracy_delta": 0.02,
                    "max_accuracy_drop": 0.01,
                },
            },
            "drift_context": {
                "severity": drift_report.severity,
                "overall_score": drift_report.drift_overall,
                "recommendations": recommendations[:3],  # top 3
            },
            "callback": {
                "on_complete": f"/training/jobs/{{job_id}}/result",
            },
        }

        # Create job record
        job = TrainingJob(
            id=str(uuid.uuid4()),
            trainer_id=trainer.id,
            drift_report_id=drift_report.id,
            field_agent_id=drift_report.agent_id,
            command_json=command,
            status="pending",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Dispatch to trainer (async HTTP, fire-and-forget)
        try:
            _dispatch_to_trainer(trainer, job, command)
            job.status = "dispatched"
            job.started_at = datetime.utcnow()
            db.commit()
            logger.info(
                "[Training] Job %s dispatched to %s for model=%s",
                job.id, trainer.name, model_name,
            )
        except Exception as e:
            job.status = "dispatch_failed"
            job.error = str(e)
            db.commit()
            logger.warning(
                "[Training] Failed to dispatch job %s to %s: %s",
                job.id, trainer.name, e,
            )

        return job

    def receive_result(
        self,
        db: Session,
        job_id: str,
        result: dict,
    ) -> TrainingJob | None:
        """Called when a trainer agent reports job completion."""
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job is None:
            return None

        success = result.get("acceptance", {}).get("gate_passed", False)
        job.result_json = result
        job.status = "completed" if success else "gate_failed"
        job.completed_at = datetime.utcnow()
        job.progress = 1.0

        if not success:
            job.error = "Model did not pass acceptance gate"

        db.commit()
        db.refresh(job)

        logger.info(
            "[Training] Job %s result: status=%s, gate_passed=%s",
            job_id, job.status, success,
        )
        return job

    def list_jobs(
        self,
        db: Session,
        trainer_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[TrainingJob]:
        q = db.query(TrainingJob)
        if trainer_id:
            q = q.filter(TrainingJob.trainer_id == trainer_id)
        if status:
            q = q.filter(TrainingJob.status == status)
        return q.order_by(TrainingJob.created_at.desc()).limit(limit).all()


def _dispatch_to_trainer(trainer: TrainerAgent, job: TrainingJob, command: dict) -> None:
    """Send the training command to the trainer agent's API."""
    url = f"{trainer.api_base_url.rstrip('/')}/api/train"
    command["job_id"] = job.id

    with httpx.Client(timeout=15) as client:
        resp = client.post(url, json=command)
        if resp.status_code not in (200, 202):
            raise RuntimeError(
                f"Trainer {trainer.name} rejected command: {resp.status_code} {resp.text[:200]}"
            )


def _infer_stage(model_name: str) -> str:
    """Infer training stage from model name."""
    name = model_name.lower()
    if "recognizer" in name or "crnn" in name or "alpr" in name:
        return "recognizer"
    if "detector" in name or "yolo" in name or "detr" in name:
        return "detector"
    return "both"


def _default_params(model_name: str) -> dict:
    """Default training parameters based on model type."""
    name = model_name.lower()
    if "recognizer" in name or "crnn" in name:
        return {"epochs": 20, "batch_size": 64, "lr": 0.0005}
    if "detector" in name or "yolo" in name:
        return {"epochs": 50, "batch_size": 16, "imgsz": 640}
    return {"epochs": 20, "batch_size": 32}
