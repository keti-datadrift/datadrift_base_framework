"""Field Agent Hub — REST API for remote field app management.

Endpoints for field applications (e.g. keti-veritas) to:
- Register themselves as field agents
- Send periodic heartbeats
- Submit drift reports from their embedded DIA systems
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services import field_agent_service as svc

router = APIRouter(prefix="/field-agents", tags=["field-agents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Request / Response schemas ──────────────────────────────────────


class RegisterRequest(BaseModel):
    app_id: str = Field(..., description="Unique identifier (e.g. 'keti-veritas-prod-01')")
    app_type: Optional[str] = Field(None, description="App category (e.g. 'video_forensics')")
    display_name: Optional[str] = None
    api_base_url: Optional[str] = Field(None, description="Agent's API URL for model push")
    api_key: Optional[str] = Field(None, description="Shared secret for authentication")
    capabilities: Optional[list[str]] = None
    registered_models: Optional[list[dict]] = None


class HeartbeatRequest(BaseModel):
    app_id: str


class DriftReportRequest(BaseModel):
    """Envelope for a DriftReport from a field agent's DIA system."""
    app_id: str = Field(..., description="Registered field agent app_id")
    report: dict = Field(..., description="Full DriftReport JSON payload")


class AgentResponse(BaseModel):
    id: str
    app_id: str
    app_type: Optional[str] = None
    display_name: Optional[str] = None
    api_base_url: Optional[str] = None
    status: str
    capabilities: Optional[list] = None
    registered_models: Optional[list] = None
    last_heartbeat: Optional[str] = None
    created_at: Optional[str] = None


class DriftReportResponse(BaseModel):
    id: str
    agent_id: str
    severity: str
    model_name: Optional[str] = None
    drift_overall: Optional[float] = None
    status: str
    created_at: Optional[str] = None


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/register", response_model=AgentResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new field agent or update an existing one.

    Idempotent: calling with the same ``app_id`` updates the existing record.
    """
    agent = svc.register_agent(
        db,
        app_id=req.app_id,
        app_type=req.app_type,
        display_name=req.display_name,
        api_base_url=req.api_base_url,
        api_key=req.api_key,
        capabilities=req.capabilities,
        registered_models=req.registered_models,
    )
    return _agent_to_response(agent)


@router.post("/heartbeat")
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db)):
    """Update heartbeat timestamp for a registered agent."""
    agent = svc.heartbeat(db, req.app_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {req.app_id}")
    return {"status": "ok", "app_id": agent.app_id, "last_heartbeat": str(agent.last_heartbeat)}


@router.post("/drift-report", response_model=DriftReportResponse)
def submit_drift_report(req: DriftReportRequest, db: Session = Depends(get_db)):
    """Receive a drift report from a field agent's DIA system.

    The report is persisted and can later be processed by the
    DriftDecisionEngine (Phase B-2).
    """
    agent = svc.get_agent_by_app_id(db, req.app_id)
    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not registered: {req.app_id}. Call /register first.",
        )

    report = svc.receive_drift_report(
        db,
        agent_id=agent.id,
        report_json=req.report,
    )

    # Stage 3.5: Autonomous loop — auto-evaluate and trigger training
    auto_result = None
    from app.services.autonomous_loop import is_auto_trigger_enabled, on_drift_report_received
    if is_auto_trigger_enabled():
        try:
            auto_result = on_drift_report_received(db, report)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("[AutoLoop] Failed: %s", e)

    resp = _report_to_response(report)
    if auto_result:
        return {**resp.__dict__, "auto_loop": auto_result}
    return resp


@router.get("/agents", response_model=list[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    """List all registered field agents."""
    agents = svc.list_agents(db)
    return [_agent_to_response(a) for a in agents]


@router.get("/reports", response_model=list[DriftReportResponse])
def list_reports(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (low/medium/high)"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List drift reports, optionally filtered by agent or severity."""
    reports = svc.list_reports(db, agent_id=agent_id, severity=severity, limit=limit)
    return [_report_to_response(r) for r in reports]


@router.get("/reports/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    """Get a single drift report with full payload."""
    from app.models import FieldDriftReport
    report = db.query(FieldDriftReport).filter(FieldDriftReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        **_report_to_response(report).__dict__,
        "report_json": report.report_json,
        "action_taken": report.action_taken,
    }


# ── Helpers ─────────────────────────────────────────────────────────


def _agent_to_response(agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        app_id=agent.app_id,
        app_type=agent.app_type,
        display_name=agent.display_name,
        api_base_url=agent.api_base_url,
        status=agent.status,
        capabilities=agent.capabilities,
        registered_models=agent.registered_models,
        last_heartbeat=str(agent.last_heartbeat) if agent.last_heartbeat else None,
        created_at=str(agent.created_at) if agent.created_at else None,
    )


def _report_to_response(report) -> DriftReportResponse:
    return DriftReportResponse(
        id=report.id,
        agent_id=report.agent_id,
        severity=report.severity,
        model_name=report.model_name,
        drift_overall=report.drift_overall,
        status=report.status,
        created_at=str(report.created_at) if report.created_at else None,
    )
