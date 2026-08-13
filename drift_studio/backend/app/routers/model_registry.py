"""Model Registry & Deployment API — manage trained model artifacts.

Endpoints for:
- Storing model artifacts from completed training jobs
- Deploying models to field agents (keti-veritas)
- Listing stored models and deployment history
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import FieldAgent, TrainingJob
from app.services.model_deployment_service import ModelDeploymentService
from app.services import promotion_gate_service
from app.services.autonomous_loop import deploy_after_promotion_approval

router = APIRouter(prefix="/deployment", tags=["deployment"])

_deploy_service = ModelDeploymentService()

# In-memory artifact store (simple — production would use DB table)
_artifacts: dict[str, dict] = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Schemas ─────────────────────────────────────────────────────────


class DeployRequest(BaseModel):
    training_job_id: str = Field(..., description="Completed training job to deploy")
    target_app_id: Optional[str] = Field(
        None, description="Deploy to specific agent (None = all eligible)"
    )


class DeployResult(BaseModel):
    artifact_id: Optional[str] = None
    model_name: Optional[str] = None
    version: Optional[str] = None
    deployments: list[dict] = Field(default_factory=list)


class ArtifactInfo(BaseModel):
    id: str
    model_name: str
    model_type: str
    version: str
    artifact_hash: str
    training_job_id: str
    status: str
    stored_at: Optional[str] = None


class PromotionInfo(BaseModel):
    id: str
    training_job_id: str
    model_name: str
    field_agent_id: Optional[str] = None
    champion_training_job_id: Optional[str] = None
    comparison: Optional[dict] = None
    status: str
    decided_by: Optional[str] = None
    decision_reason: Optional[str] = None
    created_at: Optional[str] = None
    decided_at: Optional[str] = None

    @classmethod
    def from_orm_row(cls, p) -> "PromotionInfo":
        return cls(
            id=p.id, training_job_id=p.training_job_id, model_name=p.model_name,
            field_agent_id=p.field_agent_id, champion_training_job_id=p.champion_training_job_id,
            comparison=p.comparison, status=p.status, decided_by=p.decided_by,
            decision_reason=p.decision_reason,
            created_at=p.created_at.isoformat() if p.created_at else None,
            decided_at=p.decided_at.isoformat() if p.decided_at else None,
        )


class ApproveRequest(BaseModel):
    approved_by: str = Field(..., description="Who/what approved this (human name or agent id)")
    reason: Optional[str] = None


class RejectRequest(BaseModel):
    rejected_by: str
    reason: str = Field(..., description="Why this promotion was rejected")


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/deploy", response_model=DeployResult)
def deploy_model(req: DeployRequest, db: Session = Depends(get_db)):
    """Deploy a trained model from a completed training job to field agent(s).

    Flow:
    1. Load training job result (ModelPackage)
    2. Store artifact metadata in dd
    3. Push to target field agent(s) via HTTP
    """
    job = db.query(TrainingJob).filter(TrainingJob.id == req.training_job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    if job.status != "completed":
        raise HTTPException(
            status_code=422,
            detail=f"Job status is '{job.status}', expected 'completed'",
        )

    # Store artifact metadata
    artifact_meta = _deploy_service.store_from_training_result(db, job)
    if not artifact_meta:
        raise HTTPException(status_code=422, detail="Job has no model result")

    artifact_id = artifact_meta["id"]
    _artifacts[artifact_id] = artifact_meta

    # Deploy to field agent(s)
    deployments = _deploy_service.deploy_to_all_agents(
        db,
        artifact_meta=artifact_meta,
        training_job=job,
        target_app_id=req.target_app_id,
    )

    # Round 35 — record this as the new champion for future promotion-gate
    # comparisons. A human explicitly calling this endpoint already IS the
    # approval (unlike the fully-autonomous DD_AUTO_DEPLOY path, which now
    # goes through promotion_gate_service.evaluate_promotion first) -- this
    # just fixes the previously-stubbed "what's currently deployed" gap.
    promotion_gate_service.record_manual_deployment(
        db, job, model_name=artifact_meta.get("model_name", "unknown"),
    )

    return DeployResult(
        artifact_id=artifact_id,
        model_name=artifact_meta.get("model_name"),
        version=artifact_meta.get("version"),
        deployments=deployments,
    )


# ── Promotion gate (Round 35) ──────────────────────────────────────


@router.get("/promotions", response_model=list[PromotionInfo])
def list_pending_promotions(db: Session = Depends(get_db)):
    """List challenger models awaiting champion-comparison approval
    (created by the autonomous loop when a champion already exists for
    that model/agent -- see promotion_gate_service)."""
    return [PromotionInfo.from_orm_row(p) for p in promotion_gate_service.list_pending(db)]


@router.post("/promotions/{promotion_id}/approve", response_model=PromotionInfo)
def approve_promotion(promotion_id: str, req: ApproveRequest, db: Session = Depends(get_db)):
    """Approve a pending promotion and deploy it. This is the human/agent
    review gate drift_tool_analysis.md 5부/12부 calls for -- the trainer's
    self-reported gate_passed alone no longer promotes a model once a
    champion already exists."""
    promotion = promotion_gate_service.approve_promotion(
        db, promotion_id, approved_by=req.approved_by, reason=req.reason,
    )
    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found or not pending_approval")

    job = db.query(TrainingJob).filter(TrainingJob.id == promotion.training_job_id).first()
    if job is None:
        raise HTTPException(status_code=500, detail="Promotion references a missing training job")
    deploy_after_promotion_approval(db, job, promotion)

    db.refresh(promotion)
    return PromotionInfo.from_orm_row(promotion)


@router.post("/promotions/{promotion_id}/reject", response_model=PromotionInfo)
def reject_promotion(promotion_id: str, req: RejectRequest, db: Session = Depends(get_db)):
    promotion = promotion_gate_service.reject_promotion(
        db, promotion_id, rejected_by=req.rejected_by, reason=req.reason,
    )
    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found or not pending_approval")
    return PromotionInfo.from_orm_row(promotion)


@router.get("/artifacts", response_model=list[ArtifactInfo])
def list_artifacts():
    """List all stored model artifacts."""
    return [
        ArtifactInfo(
            id=a["id"],
            model_name=a.get("model_name", ""),
            model_type=a.get("model_type", ""),
            version=a.get("version", ""),
            artifact_hash=a.get("artifact_hash", ""),
            training_job_id=a.get("training_job_id", ""),
            status=a.get("status", ""),
            stored_at=a.get("stored_at"),
        )
        for a in _artifacts.values()
    ]


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str):
    """Get full artifact metadata."""
    if artifact_id not in _artifacts:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return _artifacts[artifact_id]
