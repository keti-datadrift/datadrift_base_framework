"""Drift Decision Engine — evaluates incoming drift reports and decides action.

The "doctor's diagnosis" logic:
- LOW severity → observe (log, no action)
- MEDIUM severity → alert; if repeated for same model → escalate to retrain
- HIGH severity → retrain immediately (if retraining context available)

Actions:
- OBSERVE: log only, update report status to 'archived'
- ALERT: flag report, notify operators
- RETRAIN: trigger training via TrainingOrchestrator
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import FieldDriftReport, TrainerAgent

logger = logging.getLogger(__name__)


class Action:
    OBSERVE = "observe"
    ALERT = "alert"
    RETRAIN = "retrain"


class DriftDecision:
    """Result of evaluating a drift report."""

    def __init__(self, action: str, reason: str, trainer_name: str | None = None):
        self.action = action
        self.reason = reason
        self.trainer_name = trainer_name  # which trainer to use (for RETRAIN)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reason": self.reason,
            "trainer_name": self.trainer_name,
        }


class DriftDecisionEngine:
    """Evaluates drift reports and decides what action to take."""

    # If N medium-severity reports arrive within this window for the same
    # model, escalate to RETRAIN.
    MEDIUM_ESCALATION_COUNT = 3
    MEDIUM_ESCALATION_WINDOW_HOURS = 48

    def evaluate(self, db: Session, report: FieldDriftReport) -> DriftDecision:
        """Evaluate a single drift report and return the recommended action."""
        severity = report.severity or "low"
        model_name = report.model_name or "unknown"

        if severity == "low":
            return DriftDecision(
                action=Action.OBSERVE,
                reason=f"Low severity drift for {model_name} — observing",
            )

        if severity == "high":
            trainer = self._find_trainer(db, model_name)
            if trainer:
                return DriftDecision(
                    action=Action.RETRAIN,
                    reason=f"High severity drift for {model_name} — triggering retraining",
                    trainer_name=trainer.name,
                )
            return DriftDecision(
                action=Action.ALERT,
                reason=f"High severity drift for {model_name} — no trainer registered, alerting",
            )

        # severity == "medium"
        if self._should_escalate(db, report):
            trainer = self._find_trainer(db, model_name)
            if trainer:
                return DriftDecision(
                    action=Action.RETRAIN,
                    reason=(
                        f"Repeated medium severity drift for {model_name} "
                        f"({self.MEDIUM_ESCALATION_COUNT}+ in {self.MEDIUM_ESCALATION_WINDOW_HOURS}h) "
                        f"— escalating to retraining"
                    ),
                    trainer_name=trainer.name,
                )
        return DriftDecision(
            action=Action.ALERT,
            reason=f"Medium severity drift for {model_name} — alerting",
        )

    def _should_escalate(self, db: Session, report: FieldDriftReport) -> bool:
        """Check if recent medium-severity reports warrant escalation to RETRAIN."""
        cutoff = datetime.utcnow() - timedelta(hours=self.MEDIUM_ESCALATION_WINDOW_HOURS)
        recent_count = (
            db.query(FieldDriftReport)
            .filter(
                FieldDriftReport.agent_id == report.agent_id,
                FieldDriftReport.model_name == report.model_name,
                FieldDriftReport.severity == "medium",
                FieldDriftReport.created_at >= cutoff,
            )
            .count()
        )
        return recent_count >= self.MEDIUM_ESCALATION_COUNT

    def _find_trainer(self, db: Session, model_name: str) -> TrainerAgent | None:
        """Find a suitable trainer for the given model.

        Matching logic:
        - 'alpr' in model_name → trainer_type='alpr'
        - 'yolo' in model_name → trainer_type='yolo'
        - fallback: first active trainer
        """
        model_lower = model_name.lower()

        # Try specific match
        for keyword, trainer_type in [("alpr", "alpr"), ("yolo", "yolo"), ("detr", "yolo")]:
            if keyword in model_lower:
                trainer = (
                    db.query(TrainerAgent)
                    .filter(
                        TrainerAgent.trainer_type == trainer_type,
                        TrainerAgent.status == "active",
                    )
                    .first()
                )
                if trainer:
                    return trainer

        # Fallback: any active trainer
        return (
            db.query(TrainerAgent)
            .filter(TrainerAgent.status == "active")
            .first()
        )
