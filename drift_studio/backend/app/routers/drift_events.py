"""Drift Intervention Events API (Round 36).

사람이 "이미 알려진 의도적/일시적 변화"를 등록/조회하는 엔드포인트.
drift_corroboration_service가 이 이벤트들을 읽어 DriftDecisionEngine의
RETRAIN 판정을 보정한다 -- 여기 라우터는 등록/조회만 하고 보정 로직은
갖지 않는다.

field_agents.py에 얹지 않은 이유: 그쪽은 현장 에이전트가 스스로 호출하는
기계 대 기계 인터페이스라, 사람이 이벤트를 등록하는 것과 신뢰 경계가
다르다. training.py에 얹지 않은 이유: training.py는 이미 FieldDriftReport를
읽기만 하고 그 등록/조회 엔드포인트는 소유하지 않는다("읽는 쪽이 소유자는
아니다") -- 같은 원칙을 여기도 적용.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import DriftInterventionEvent
from app.services import drift_corroboration_service as corroboration

router = APIRouter(prefix="/drift-events", tags=["drift-events"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RegisterInterventionRequest(BaseModel):
    model_name: str = Field(..., description="FieldDriftReport.model_name과 정확히 일치해야 매칭됨")
    field_agent_id: Optional[str] = Field(None, description="생략/null = 이 모델을 쓰는 모든 에이전트에 적용")
    start_at: datetime
    end_at: Optional[datetime] = Field(None, description="생략/null = 아직 진행 중")
    description: str = Field(..., description="예: '카메라 캘리브레이션 재조정', '펌웨어 v2.3 배포'")
    confirmed: bool = Field(True, description="True = 즉시 신뢰(사람이 등록); False = 후보로만 보여지고 판정엔 영향 없음")
    proposed_by: str = "human"


class InterventionEventResponse(BaseModel):
    id: str
    model_name: str
    field_agent_id: Optional[str] = None
    start_at: str
    end_at: Optional[str] = None
    description: Optional[str] = None
    confirmed: bool
    proposed_by: Optional[str] = None
    created_at: Optional[str] = None


def _to_response(e: DriftInterventionEvent) -> InterventionEventResponse:
    return InterventionEventResponse(
        id=e.id, model_name=e.model_name, field_agent_id=e.field_agent_id,
        start_at=e.start_at.isoformat() if e.start_at else None,
        end_at=e.end_at.isoformat() if e.end_at else None,
        description=e.description, confirmed=e.confirmed, proposed_by=e.proposed_by,
        created_at=e.created_at.isoformat() if e.created_at else None,
    )


@router.post("/interventions", response_model=InterventionEventResponse)
def register_intervention(req: RegisterInterventionRequest, db: Session = Depends(get_db)):
    if req.end_at is not None and req.end_at < req.start_at:
        raise HTTPException(status_code=422, detail="end_at must not be before start_at")
    event = corroboration.register_intervention_event(
        db, model_name=req.model_name, field_agent_id=req.field_agent_id,
        start_at=req.start_at, end_at=req.end_at, description=req.description,
        confirmed=req.confirmed, proposed_by=req.proposed_by,
    )
    return _to_response(event)


@router.get("/interventions", response_model=list[InterventionEventResponse])
def list_interventions(
    model_name: Optional[str] = Query(None),
    field_agent_id: Optional[str] = Query(None),
    confirmed: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    events = corroboration.list_intervention_events(
        db, model_name=model_name, field_agent_id=field_agent_id, confirmed=confirmed, limit=limit,
    )
    return [_to_response(e) for e in events]


@router.get("/interventions/{event_id}", response_model=InterventionEventResponse)
def get_intervention(event_id: str, db: Session = Depends(get_db)):
    event = db.query(DriftInterventionEvent).filter(DriftInterventionEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Intervention event not found")
    return _to_response(event)
