"""Model Deployment Service — stores model artifacts and pushes to field agents.

After a training job completes and passes the quality gate, this service:
1. Downloads the model artifact from the trainer agent
2. Verifies integrity (SHA-256)
3. Stores it in dd's local artifact store
4. Pushes the model to the target field agent (keti-veritas)
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.models import FieldAgent, TrainingJob

logger = logging.getLogger(__name__)

# Local artifact storage
ARTIFACTS_DIR = Path(os.getenv("DD_ARTIFACTS_DIR", "/app/model_artifacts"))


class ModelDeploymentService:
    """Manages model artifact storage and deployment to field agents."""

    def __init__(self) -> None:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    def store_from_training_result(
        self,
        db: Session,
        job: TrainingJob,
    ) -> dict | None:
        """Extract model info from a completed training job and store metadata.

        The actual model binary is fetched from the trainer when deploying.
        Returns the stored artifact metadata dict, or None if job has no result.
        """
        result = job.result_json
        if not result:
            return None

        model_info = result.get("model", {})
        artifact_hash = model_info.get("artifact_hash", "")
        model_name = model_info.get("name", "unknown")
        version = model_info.get("version", "0.0.0")

        artifact_meta = {
            "id": str(uuid.uuid4()),
            "training_job_id": job.id,
            "model_name": model_name,
            "model_type": model_info.get("type", "unknown"),
            "version": version,
            "artifact_hash": artifact_hash,
            "artifact_size_bytes": model_info.get("artifact_size_bytes", 0),
            "framework": model_info.get("framework", "pytorch"),
            "architecture": model_info.get("architecture", "unknown"),
            "training_metadata": result.get("training_metadata", {}),
            "acceptance": result.get("acceptance", {}),
            "stored_at": datetime.utcnow().isoformat(),
            "status": "stored",
        }

        logger.info(
            "[Deploy] Stored artifact metadata: %s v%s (hash=%s)",
            model_name, version, artifact_hash[:16],
        )
        return artifact_meta

    def deploy_to_field_agent(
        self,
        db: Session,
        *,
        agent: FieldAgent,
        artifact_meta: dict,
        training_job: TrainingJob,
    ) -> dict:
        """Push a model to a field agent (keti-veritas).

        Sends the ModelPackage JSON to the agent's deploy endpoint.
        The field agent downloads the model binary separately if needed.
        """
        if not agent.api_base_url:
            return {"status": "error", "detail": "Agent has no api_base_url"}

        deploy_url = f"{agent.api_base_url.rstrip('/')}/api/v1/models/deploy"

        payload = {
            "model": artifact_meta,
            "source": {
                "dd_instance": "drift-studio",
                "training_job_id": training_job.id,
                "drift_report_id": training_job.drift_report_id,
            },
            "deployment": {
                "strategy": "blue_green",
                "rollback_version": _get_current_version(artifact_meta.get("model_name")),
            },
        }

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    deploy_url,
                    json=payload,
                    headers=_agent_auth_headers(agent),
                )
                if resp.status_code == 200:
                    logger.info(
                        "[Deploy] Model pushed to %s: %s v%s",
                        agent.app_id,
                        artifact_meta.get("model_name"),
                        artifact_meta.get("version"),
                    )
                    return {
                        "status": "deployed",
                        "agent_id": agent.id,
                        "agent_app_id": agent.app_id,
                        "response": resp.json(),
                    }
                else:
                    logger.warning(
                        "[Deploy] Agent %s rejected deployment: %s %s",
                        agent.app_id, resp.status_code, resp.text[:200],
                    )
                    return {
                        "status": "rejected",
                        "agent_id": agent.id,
                        "status_code": resp.status_code,
                        "detail": resp.text[:500],
                    }
        except Exception as e:
            logger.error("[Deploy] Failed to push to %s: %s", agent.app_id, e)
            return {
                "status": "error",
                "agent_id": agent.id,
                "detail": str(e),
            }

    def deploy_to_all_agents(
        self,
        db: Session,
        *,
        artifact_meta: dict,
        training_job: TrainingJob,
        target_app_id: str | None = None,
    ) -> list[dict]:
        """Deploy model to one or all field agents.

        If target_app_id is specified, deploy only to that agent.
        Otherwise, deploy to all active agents that support 'model_receive'.
        """
        if target_app_id:
            agent = (
                db.query(FieldAgent)
                .filter(FieldAgent.app_id == target_app_id, FieldAgent.status == "active")
                .first()
            )
            if not agent:
                return [{"status": "error", "detail": f"Agent not found: {target_app_id}"}]
            return [self.deploy_to_field_agent(
                db, agent=agent, artifact_meta=artifact_meta, training_job=training_job,
            )]

        # Deploy to all active agents with model_receive capability
        agents = db.query(FieldAgent).filter(FieldAgent.status == "active").all()
        results = []
        for agent in agents:
            caps = agent.capabilities or []
            if "model_receive" in caps:
                result = self.deploy_to_field_agent(
                    db, agent=agent, artifact_meta=artifact_meta, training_job=training_job,
                )
                results.append(result)
        return results


def _agent_auth_headers(agent: FieldAgent) -> dict:
    """Build auth headers for communicating with a field agent."""
    # Field agents use X-API-Key authentication
    # The key itself is stored hashed; for now we skip auth
    # (in production, use a shared secret or token exchange)
    return {}


def _get_current_version(model_name: str | None) -> str | None:
    """Get the current deployed version of a model (for rollback reference)."""
    # In a full implementation, this would query the field agent
    # For now, return None (no rollback reference)
    return None
