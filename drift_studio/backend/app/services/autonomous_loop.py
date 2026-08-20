"""Autonomous Loop — fully automated drift → retrain → deploy pipeline.

When DD_AUTO_TRIGGER=true, incoming drift reports are automatically:
1. Evaluated by DriftDecisionEngine, then corroborated against known
   intervention events (drift_corroboration_service, Round 36)
2. If action=retrain → training dispatched to trainer agent
3. On training completion → model deployed to field agent

This is the "Stage 3.5" self-evolving loop.

Safety:
- Only triggers on medium (repeated) or high severity
- A confirmed, overlapping intervention event downgrades retrain to alert
  instead of triggering blindly (Round 36)
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
from app.services.drift_decision_engine import Action
from app.services import drift_corroboration_service
from app.services.training_orchestrator import TrainingOrchestrator
from app.services.model_deployment_service import ModelDeploymentService
from app.services import promotion_gate_service

logger = logging.getLogger(__name__)

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

    # Step 1: Evaluate (+ event-based corroboration, Round 36)
    decision = drift_corroboration_service.evaluate_corroborated(db, report)
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
            "corroboration": decision.corroboration,
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

    # Promotion gate (drift_tool_analysis.md 5부/12부) — the trainer's own
    # self-reported gate_passed is necessary but not sufficient. If a
    # champion is already deployed for this (model, agent), an independent
    # human/agent approval is required before this fully-autonomous path
    # (no human in the loop otherwise) is allowed to deploy. First-ever
    # deployment for a (model, agent) pair auto-approves — nothing to
    # compare against yet.
    model_name = (
        (job.result_json or {}).get("model", {}).get("name")
        or (job.command_json or {}).get("training", {}).get("pipeline")
        or "unknown"
    )
    promotion = promotion_gate_service.evaluate_promotion(db, job, model_name=model_name)

    if promotion.status != "auto_approved":
        logger.info(
            "[AutoLoop] Training job %s: promotion %s requires approval — deploy deferred (%s)",
            job.id, promotion.id, promotion.decision_reason,
        )
        return {
            "auto_deploy": True,
            "action": "pending_approval",
            "promotion_id": promotion.id,
            "reason": promotion.decision_reason,
            "comparison": promotion.comparison,
        }

    deployments, artifact_meta = _deploy_job(db, job)
    if artifact_meta is None:
        return {"auto_deploy": True, "action": "skipped", "reason": "no_model_result"}
    promotion_gate_service.mark_deployed(db, promotion.id)

    logger.info(
        "[AutoLoop] Auto-deployed model from job %s → %d agent(s) (promotion=%s)",
        job.id, len(deployments), promotion.id,
    )

    return {
        "auto_deploy": True,
        "action": "deployed",
        "artifact_id": artifact_meta.get("id"),
        "deployments": deployments,
        "promotion_id": promotion.id,
    }


def _deploy_job(db: Session, job: TrainingJob):
    """Shared deploy step -- used both by the auto-approved path above and
    by `deploy_after_promotion_approval` once a pending_approval promotion
    is later approved via the API."""
    artifact_meta = _deploy_service.store_from_training_result(db, job)
    if not artifact_meta:
        return [], None

    target_app_id = job.field_agent_id
    from app.models import FieldAgent
    if target_app_id:
        agent = db.query(FieldAgent).filter(FieldAgent.id == target_app_id).first()
        target_app_id = agent.app_id if agent else None

    deployments = _deploy_service.deploy_to_all_agents(
        db, artifact_meta=artifact_meta, training_job=job, target_app_id=target_app_id,
    )
    return deployments, artifact_meta


def deploy_after_promotion_approval(db: Session, job: TrainingJob, promotion) -> dict:
    """Called by the approval endpoint once a pending_approval promotion is
    approved -- performs the deployment that on_training_completed deferred."""
    deployments, artifact_meta = _deploy_job(db, job)
    if artifact_meta is None:
        return {"action": "skipped", "reason": "no_model_result"}
    promotion_gate_service.mark_deployed(db, promotion.id)
    logger.info(
        "[AutoLoop] Deployed model from job %s after promotion approval (promotion=%s)",
        job.id, promotion.id,
    )
    return {"action": "deployed", "artifact_id": artifact_meta.get("id"), "deployments": deployments}
