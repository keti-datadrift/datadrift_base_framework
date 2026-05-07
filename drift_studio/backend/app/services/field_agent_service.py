"""Field Agent management service.

Handles registration, heartbeat, and drift report intake from
remote field applications (e.g. keti-veritas).
"""

import hashlib
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import FieldAgent, FieldDriftReport


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def register_agent(
    db: Session,
    *,
    app_id: str,
    app_type: str | None = None,
    display_name: str | None = None,
    api_base_url: str | None = None,
    api_key: str | None = None,
    capabilities: list[str] | None = None,
    registered_models: list[dict] | None = None,
) -> FieldAgent:
    """Register or update a field agent."""
    existing = db.query(FieldAgent).filter(FieldAgent.app_id == app_id).first()

    if existing:
        # Update
        if app_type is not None:
            existing.app_type = app_type
        if display_name is not None:
            existing.display_name = display_name
        if api_base_url is not None:
            existing.api_base_url = api_base_url
        if api_key is not None:
            existing.api_key_hash = hash_api_key(api_key)
        if capabilities is not None:
            existing.capabilities = capabilities
        if registered_models is not None:
            existing.registered_models = registered_models
        existing.status = "active"
        existing.last_heartbeat = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    # Create new
    agent = FieldAgent(
        id=str(uuid.uuid4()),
        app_id=app_id,
        app_type=app_type,
        display_name=display_name or app_id,
        api_base_url=api_base_url,
        api_key_hash=hash_api_key(api_key) if api_key else None,
        status="active",
        capabilities=capabilities or ["drift_report"],
        registered_models=registered_models,
        last_heartbeat=datetime.utcnow(),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def heartbeat(db: Session, app_id: str) -> FieldAgent | None:
    """Update heartbeat timestamp. Returns None if agent not found."""
    agent = db.query(FieldAgent).filter(FieldAgent.app_id == app_id).first()
    if agent is None:
        return None
    agent.last_heartbeat = datetime.utcnow()
    agent.status = "active"
    db.commit()
    db.refresh(agent)
    return agent


def receive_drift_report(
    db: Session,
    *,
    agent_id: str,
    report_json: dict,
) -> FieldDriftReport:
    """Persist a drift report from a field agent."""
    drift = report_json.get("drift", {})
    severity = drift.get("severity", "low")
    model_name = drift.get("model_name")
    overall = drift.get("scores", {}).get("overall")

    report = FieldDriftReport(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        report_json=report_json,
        severity=severity,
        model_name=model_name,
        drift_overall=overall,
        status="received",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def list_agents(db: Session) -> list[FieldAgent]:
    return db.query(FieldAgent).order_by(FieldAgent.created_at.desc()).all()


def list_reports(
    db: Session,
    agent_id: str | None = None,
    severity: str | None = None,
    limit: int = 50,
) -> list[FieldDriftReport]:
    q = db.query(FieldDriftReport)
    if agent_id:
        q = q.filter(FieldDriftReport.agent_id == agent_id)
    if severity:
        q = q.filter(FieldDriftReport.severity == severity)
    return q.order_by(FieldDriftReport.created_at.desc()).limit(limit).all()


def get_agent_by_app_id(db: Session, app_id: str) -> FieldAgent | None:
    return db.query(FieldAgent).filter(FieldAgent.app_id == app_id).first()
