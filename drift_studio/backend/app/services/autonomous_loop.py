"""Autonomous Loop — fully automated drift → retrain → deploy pipeline.

When DD_AUTO_TRIGGER=true, incoming drift reports are automatically:
1. Evaluated by DriftDecisionEngine
2. If action=retrain → training dispatched to trainer agent
3. On training completion → model deployed to field agent

This is the "Stage 3.5" self-evolving loop.

Safety:
- Only triggers on medium (repeated) or high severity
- Quality gate must pass on trainer side
- Field agent can reject deployment (DD_AUTO_ACCEPT_MODELS)
- All actions are logged in TrainingJob and FieldDriftReport
"""

from __future__ import annotations

import logging
import os
import threading

from sqlalchemy.orm import Session

from app.models import FieldDriftReport, TrainingJob
from app.services.drift_decision_engine import Action, DriftDecisionEngine
from app.services.training_orchestrator import TrainingOrchestrator
from app.services.model_deployment_service import ModelDeploymentService

logger = logging.getLogger(__name__)

_decision_engine = DriftDecisionEngine()
_orchestrator = TrainingOrchestrator()
_deploy_service = ModelDeploymentService()


def is_auto_trigger_enabled() -> bool:
    return os.getenv("DD_AUTO_TRIGGER", "false").lower() == "true"


def is_auto_deploy_enabled() -> bool:
    return os.getenv("DD_AUTO_DEPLOY", "false").lower() == "true"


def on_drift_report_received(db: Session, report: FieldDriftReport) -> dict:
    """Called after a drift report is persisted. Runs the autonomous loop if enabled.

    Returns a summary dict of what happened.
    """
    if not is_auto_trigger_enabled():
        return {"auto_trigger": False, "action": "manual_review_required"}

    # Step 1: Evaluate
    decision = _decision_engine.evaluate(db, report)
    logger.info(
        "[AutoLoop] Report %s: severity=%s → action=%s",
        report.id, report.severity, decision.action,
    )

    # Update report with decision
    report.action_taken = decision.to_dict()

    if decision.action != Action.RETRAIN:
        report.status = decision.action
        db.commit()
        return {
            "auto_trigger": True,
            "action": decision.action,
            "reason": decision.reason,
        }

    # Step 2: Trigger training
    from app.models import TrainerAgent
    trainer = None
    if decision.trainer_name:
        trainer = db.query(TrainerAgent).filter(
            TrainerAgent.name == decision.trainer_name
        ).first()

    if not trainer:
        report.status = "alert"
        db.commit()
        logger.warning("[AutoLoop] No trainer for %s — alerting only", report.model_name)
        return {
            "auto_trigger": True,
            "action": "alert",
            "reason": f"retrain decided but no trainer: {decision.trainer_name}",
        }

    job = _orchestrator.trigger_training(db, trainer=trainer, drift_report=report)
    report.status = "action_taken"
    report.action_taken = {
        **decision.to_dict(),
        "training_job_id": job.id,
        "auto_triggered": True,
    }
    db.commit()

    logger.info(
        "[AutoLoop] Training triggered: job=%s trainer=%s model=%s",
        job.id, trainer.name, report.model_name,
    )

    return {
        "auto_trigger": True,
        "action": "retrain",
        "training_job_id": job.id,
        "trainer": trainer.name,
    }


def on_training_completed(db: Session, job: TrainingJob) -> dict:
    """Called when a training job completes. Auto-deploys if enabled.

    Returns a summary dict.
    """
    if not is_auto_deploy_enabled():
        return {"auto_deploy": False, "action": "manual_deploy_required"}

    if job.status != "completed":
        return {"auto_deploy": False, "action": "skipped", "reason": f"job status: {job.status}"}

    # Check quality gate
    result = job.result_json or {}
    acceptance = result.get("acceptance", {})
    gate_passed = acceptance.get("gate_passed", False)

    if not gate_passed:
        logger.info("[AutoLoop] Training job %s: quality gate failed — skipping deploy", job.id)
        return {
            "auto_deploy": True,
            "action": "skipped",
            "reason": "quality_gate_failed",
            "metrics": acceptance,
        }

    # Store artifact metadata
    artifact_meta = _deploy_service.store_from_training_result(db, job)
    if not artifact_meta:
        return {"auto_deploy": True, "action": "skipped", "reason": "no_model_result"}

    # Deploy to the field agent that triggered the drift report
    target_app_id = job.field_agent_id
    from app.models import FieldAgent
    if target_app_id:
        agent = db.query(FieldAgent).filter(FieldAgent.id == target_app_id).first()
        target_app_id = agent.app_id if agent else None

    deployments = _deploy_service.deploy_to_all_agents(
        db,
        artifact_meta=artifact_meta,
        training_job=job,
        target_app_id=target_app_id,
    )

    logger.info(
        "[AutoLoop] Auto-deployed model from job %s → %d agent(s)",
        job.id, len(deployments),
    )

    return {
        "auto_deploy": True,
        "action": "deployed",
        "artifact_id": artifact_meta.get("id"),
        "deployments": deployments,
    }
