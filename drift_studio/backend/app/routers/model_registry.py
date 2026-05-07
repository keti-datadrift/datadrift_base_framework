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

    return DeployResult(
        artifact_id=artifact_id,
        model_name=artifact_meta.get("model_name"),
        version=artifact_meta.get("version"),
        deployments=deployments,
    )


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
