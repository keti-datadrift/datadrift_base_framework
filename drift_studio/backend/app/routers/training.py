"""Training Orchestration API — manage trainers and training jobs.

Endpoints for:
- Registering trainer agents (e.g. alpr training server)
- Triggering training from drift reports
- Receiving training results (callback from trainer)
- Listing jobs and their status
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import FieldDriftReport, TrainerAgent, TrainingJob
from app.services.drift_decision_engine import DriftDecisionEngine, Action
from app.services.training_orchestrator import TrainingOrchestrator

router = APIRouter(prefix="/training", tags=["training"])

_decision_engine = DriftDecisionEngine()
_orchestrator = TrainingOrchestrator()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Schemas ─────────────────────────────────────────────────────────


class RegisterTrainerRequest(BaseModel):
    name: str = Field(..., description="Unique trainer name (e.g. 'alpr-trainer')")
    trainer_type: Optional[str] = Field(None, description="e.g. 'alpr', 'yolo'")
    api_base_url: str = Field(..., description="Trainer API URL (e.g. 'http://alpr:8090')")
    api_key: Optional[str] = None
    capabilities: Optional[list[str]] = None


class TriggerTrainingRequest(BaseModel):
    drift_report_id: str = Field(..., description="ID of the drift report triggering training")
    trainer_name: Optional[str] = Field(None, description="Override trainer (default: auto-select)")
    params: Optional[dict] = Field(None, description="Override training parameters")


class TrainingResultCallback(BaseModel):
    """Received from trainer agent when training completes."""
    job_id: str
    result: dict = Field(..., description="ModelPackage or error details")


class TrainerResponse(BaseModel):
    id: str
    name: str
    trainer_type: Optional[str] = None
    api_base_url: str
    status: str
    capabilities: Optional[list] = None
    last_heartbeat: Optional[str] = None


class TrainingJobResponse(BaseModel):
    id: str
    trainer_id: str
    drift_report_id: Optional[str] = None
    status: str
    progress: float
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ── Trainer Management ──────────────────────────────────────────────


@router.post("/trainers/register", response_model=TrainerResponse)
def register_trainer(req: RegisterTrainerRequest, db: Session = Depends(get_db)):
    """Register a new trainer agent (idempotent)."""
    import hashlib
    import uuid as _uuid

    existing = db.query(TrainerAgent).filter(TrainerAgent.name == req.name).first()
    if existing:
        existing.api_base_url = req.api_base_url
        existing.trainer_type = req.trainer_type
        if req.api_key:
            existing.api_key_hash = hashlib.sha256(req.api_key.encode()).hexdigest()
        if req.capabilities:
            existing.capabilities = req.capabilities
        existing.status = "active"
        db.commit()
        db.refresh(existing)
        return _trainer_response(existing)

    agent = TrainerAgent(
        id=str(_uuid.uuid4()),
        name=req.name,
        trainer_type=req.trainer_type,
        api_base_url=req.api_base_url,
        api_key_hash=hashlib.sha256(req.api_key.encode()).hexdigest() if req.api_key else None,
        capabilities=req.capabilities,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _trainer_response(agent)


@router.get("/trainers", response_model=list[TrainerResponse])
def list_trainers(db: Session = Depends(get_db)):
    """List all registered trainer agents."""
    trainers = db.query(TrainerAgent).order_by(TrainerAgent.created_at.desc()).all()
    return [_trainer_response(t) for t in trainers]


# ── Decision + Training Trigger ─────────────────────────────────────


@router.post("/evaluate/{report_id}")
def evaluate_drift_report(report_id: str, db: Session = Depends(get_db)):
    """Evaluate a drift report and return the recommended action.

    Does NOT trigger training — use /trigger for that.
    """
    report = db.query(FieldDriftReport).filter(FieldDriftReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Drift report not found")

    decision = _decision_engine.evaluate(db, report)
    return {
        "report_id": report_id,
        "severity": report.severity,
        "model_name": report.model_name,
        "decision": decision.to_dict(),
    }


@router.post("/trigger", response_model=TrainingJobResponse)
def trigger_training(req: TriggerTrainingRequest, db: Session = Depends(get_db)):
    """Trigger training based on a drift report.

    1. Evaluates the drift report
    2. If action is RETRAIN, dispatches a training command
    3. Returns the training job record
    """
    report = db.query(FieldDriftReport).filter(
        FieldDriftReport.id == req.drift_report_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Drift report not found")

    # Evaluate
    decision = _decision_engine.evaluate(db, report)

    if decision.action != Action.RETRAIN:
        # Update report status and return
        report.status = decision.action
        report.action_taken = decision.to_dict()
        db.commit()
        raise HTTPException(
            status_code=422,
            detail=f"Decision is '{decision.action}', not retrain: {decision.reason}",
        )

    # Find trainer
    trainer_name = req.trainer_name or decision.trainer_name
    if not trainer_name:
        raise HTTPException(status_code=422, detail="No trainer available for this model")

    trainer = db.query(TrainerAgent).filter(TrainerAgent.name == trainer_name).first()
    if not trainer:
        raise HTTPException(status_code=404, detail=f"Trainer not found: {trainer_name}")

    # Dispatch
    job = _orchestrator.trigger_training(
        db,
        trainer=trainer,
        drift_report=report,
        training_params=req.params,
    )

    # Update drift report status
    report.status = "action_taken"
    report.action_taken = {**decision.to_dict(), "training_job_id": job.id}
    db.commit()

    return _job_response(job)


# ── Training Job Management ─────────────────────────────────────────


@router.get("/jobs", response_model=list[TrainingJobResponse])
def list_jobs(
    trainer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List training jobs."""
    jobs = _orchestrator.list_jobs(db, trainer_id=trainer_id, status=status, limit=limit)
    return [_job_response(j) for j in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a training job with full command and result."""
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return {
        **_job_response(job).__dict__,
        "command_json": job.command_json,
        "result_json": job.result_json,
        "field_agent_id": job.field_agent_id,
    }


@router.post("/jobs/{job_id}/result")
def receive_training_result(job_id: str, body: TrainingResultCallback, db: Session = Depends(get_db)):
    """Callback endpoint for trainer agents to report results."""
    job = _orchestrator.receive_result(db, job_id, body.result)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")

    # Stage 3.5: Autonomous loop — auto-deploy on completion
    auto_result = None
    from app.services.autonomous_loop import is_auto_deploy_enabled, on_training_completed
    if is_auto_deploy_enabled():
        try:
            auto_result = on_training_completed(db, job)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("[AutoLoop] Auto-deploy failed: %s", e)

    resp = {"status": "ok", "job_id": job.id, "job_status": job.status}
    if auto_result:
        resp["auto_deploy"] = auto_result
    return resp


# ── Helpers ─────────────────────────────────────────────────────────


def _trainer_response(t: TrainerAgent) -> TrainerResponse:
    return TrainerResponse(
        id=t.id,
        name=t.name,
        trainer_type=t.trainer_type,
        api_base_url=t.api_base_url,
        status=t.status,
        capabilities=t.capabilities,
        last_heartbeat=str(t.last_heartbeat) if t.last_heartbeat else None,
    )


def _job_response(j: TrainingJob) -> TrainingJobResponse:
    return TrainingJobResponse(
        id=j.id,
        trainer_id=j.trainer_id,
        drift_report_id=j.drift_report_id,
        status=j.status,
        progress=j.progress,
        error=j.error,
        created_at=str(j.created_at) if j.created_at else None,
        started_at=str(j.started_at) if j.started_at else None,
        completed_at=str(j.completed_at) if j.completed_at else None,
    )
