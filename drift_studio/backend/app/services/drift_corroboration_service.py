"""Drift Decision Engine 이벤트 보정 레이어 (Round 36).

context_workplace/drift_tool_analysis.md 3부(레벨4 개입보정)·12부(설명
후보이지 확정이 아니다, 자동화된 주장을 과신하지 않는다)를 이 백엔드에
적용한 것 -- promotion_gate_service.py(Round 35)가 재학습 결과의 자체보고
gate_passed를 블라인드로 믿지 않게 만든 것과 정확히 같은 원칙을, 파이프라인
반대쪽 끝(재학습 결과가 아니라 드리프트 판정 자체)에 적용한다.
DriftDecisionEngine.evaluate()는 필드 에이전트가 자체 계산해 보고한
severity 문자열만 보고 RETRAIN까지 결정하며 독립적인 corroboration이
없었다.

ddoc_plugin_reference_engine/event_store.py의 intervention_log와 같은
설계 vocabulary를 쓰되 코드는 공유하지 않는다 -- 그건 데이터셋 스코프의
로컬 YAML 파일이라 이 백엔드 프로세스가 읽을 수 있는 대상이 아니다(다른
프로세스, 다른 스코프 키). 여기서는 (model_name, field_agent_id) 스코프의
own 테이블(DriftInterventionEvent)로 같은 아이디어를 재구성한다. regime류
(영구 재정의) 이벤트는 다루지 않는다 -- DriftDecisionEngine은 애초에 자체
기준선 개념이 없어서 "재정의"할 대상이 없다.

DriftDecisionEngine.evaluate()의 내부는 건드리지 않는다 -- evaluate_corroborated()가
그 결과를 감싸는 wrapper이고, 3개 호출부(training.py의 /evaluate·/trigger,
autonomous_loop.py의 자동루프) 전부 이 wrapper를 쓴다. 신뢰도 점수는 만들지
않는다 -- 매칭된 이벤트와 그 설명만 그대로 보여준다(가짜 정밀도를 만들지
않는 것 자체가 12부의 원칙).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import DriftInterventionEvent, FieldDriftReport
from app.services.drift_decision_engine import Action, DriftDecision, DriftDecisionEngine

_engine = DriftDecisionEngine()


class CorroboratedDecision:
    """DriftDecision과 같은 표면(.action/.reason/.trainer_name/.to_dict())을
    가져서, 호출부가 어느 쪽을 받았는지 신경 쓰지 않고 그대로 쓸 수 있다."""

    def __init__(self, action: str, reason: str, trainer_name: str | None = None, *,
                 original_action: str | None = None, corroboration: dict | None = None):
        self.action = action
        self.reason = reason
        self.trainer_name = trainer_name
        self.original_action = original_action or action
        self.corroboration = corroboration or {"checked": False, "matched_events": []}

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reason": self.reason,
            "trainer_name": self.trainer_name,
            "original_action": self.original_action,
            "corroboration": self.corroboration,
        }


def evaluate_corroborated(db: Session, report: FieldDriftReport) -> CorroboratedDecision:
    """DriftDecisionEngine.evaluate()의 드롭인 대체 -- 3개 호출부 전부 이걸
    쓴다. 엔진을 그대로 호출한 뒤, RETRAIN이거나 트레이너 부재로 에스컬레이션이
    억눌린 medium ALERT일 때만 겹치는 이벤트를 확인한다."""
    decision = _engine.evaluate(db, report)

    if not _needs_check(db, report, decision):
        return CorroboratedDecision(decision.action, decision.reason, decision.trainer_name)

    matches = _find_matching_events(db, report)
    if not matches:
        return CorroboratedDecision(
            decision.action, decision.reason, decision.trainer_name,
            corroboration={"checked": True, "matched_events": []},
        )

    summaries = [_event_summary(e) for e in matches]
    confirmed = [e for e in matches if e.confirmed]

    if not confirmed:
        # 후보(candidate)만 있음 -- 보여주되(안 숨김) 결정에는 반영 안 함.
        # ddoc 쪽 "agent proposes, human approves" 관례와 동일.
        return CorroboratedDecision(
            decision.action, decision.reason, decision.trainer_name,
            corroboration={"checked": True, "matched_events": summaries},
        )

    downgraded = Action.ALERT if decision.action == Action.RETRAIN else decision.action
    labels = ", ".join(e.description or e.id for e in confirmed)
    if downgraded != decision.action:
        change_note = f"'{decision.action}'에서 '{downgraded}'로 하향"
    else:
        change_note = f"'{decision.action}' 유지(더 낮출 액션이 없음)"
    reason = (
        f"{decision.reason} — {change_note}: 겹치는 확정 개입 이벤트가 있음"
        f"({labels}). 사람이 검토할 설명 후보일 뿐 확정된 원인이 아님(12부)."
    )
    return CorroboratedDecision(
        downgraded, reason,
        trainer_name=decision.trainer_name if downgraded == Action.RETRAIN else None,
        original_action=decision.action,
        corroboration={"checked": True, "matched_events": summaries},
    )


def _needs_check(db: Session, report: FieldDriftReport, decision: DriftDecision) -> bool:
    if decision.action == Action.RETRAIN:
        return True
    if decision.action == Action.ALERT and report.severity == "medium":
        # medium이 반복 임계값을 넘었는데 등록된 트레이너가 없어 RETRAIN
        # 대신 ALERT가 나온 경우도 같은 모양의 ALERT라 DriftDecision만으로는
        # 구분이 안 된다(코드 확인함) -- evaluate() 내부는 안 건드리는
        # 원칙이라, 같은 패키지 내 sibling 서비스로서 판별 메서드를 재사용한다.
        return _engine._should_escalate(db, report)
    return False


def _find_matching_events(db: Session, report: FieldDriftReport) -> list[DriftInterventionEvent]:
    if not report.model_name:
        return []
    as_of = report.created_at or datetime.utcnow()  # 평가 시점의 wall-clock now가 아니라 수집 시점 기준
    q = db.query(DriftInterventionEvent).filter(
        DriftInterventionEvent.model_name == report.model_name,  # 정확일치만 (과매칭이 더 위험)
        DriftInterventionEvent.start_at <= as_of,
        or_(DriftInterventionEvent.end_at.is_(None), DriftInterventionEvent.end_at >= as_of),
    )
    # 주의: FieldDriftReport의 컬럼명은 agent_id (다른 테이블들의 field_agent_id와 다름)
    if report.agent_id:
        q = q.filter(or_(
            DriftInterventionEvent.field_agent_id.is_(None),
            DriftInterventionEvent.field_agent_id == report.agent_id,
        ))
    else:
        q = q.filter(DriftInterventionEvent.field_agent_id.is_(None))
    return q.order_by(DriftInterventionEvent.start_at.desc()).all()


def _event_summary(e: DriftInterventionEvent) -> dict:
    # action_taken은 JSON 컬럼 -- raw datetime을 넣으면 commit 시 에러(Round 34의
    # NaN-in-JSON 버그와 같은 종류). 여기서 전부 문자열로 바꿔둔다.
    return {
        "id": e.id, "model_name": e.model_name, "field_agent_id": e.field_agent_id,
        "start_at": e.start_at.isoformat() if e.start_at else None,
        "end_at": e.end_at.isoformat() if e.end_at else None,
        "description": e.description, "confirmed": e.confirmed, "proposed_by": e.proposed_by,
    }


def _to_naive_utc(dt: datetime) -> datetime:
    """이 코드베이스 전체가 naive UTC(datetime.utcnow(), func.now())라서,
    API로 들어온 tzinfo가 있는 값도 벗겨서 맞춘다 -- 안 맞추면 SQLite가
    텍스트로 저장/비교하면서 에러 없이 조용히 잘못 비교된다."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# ── 등록/조회 (app/routers/drift_events.py가 사용) ──────────────────────

def register_intervention_event(db: Session, *, model_name: str, field_agent_id: str | None,
                                 start_at: datetime, end_at: datetime | None, description: str,
                                 confirmed: bool = True, proposed_by: str = "human") -> DriftInterventionEvent:
    event = DriftInterventionEvent(
        id=str(uuid.uuid4()), model_name=model_name, field_agent_id=field_agent_id,
        start_at=_to_naive_utc(start_at), end_at=_to_naive_utc(end_at) if end_at else None,
        description=description, confirmed=confirmed, proposed_by=proposed_by,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_intervention_events(db: Session, *, model_name: str | None = None,
                              field_agent_id: str | None = None, confirmed: bool | None = None,
                              limit: int = 100) -> list[DriftInterventionEvent]:
    q = db.query(DriftInterventionEvent)
    if model_name:
        q = q.filter(DriftInterventionEvent.model_name == model_name)
    if field_agent_id:
        q = q.filter(DriftInterventionEvent.field_agent_id == field_agent_id)
    if confirmed is not None:
        q = q.filter(DriftInterventionEvent.confirmed == confirmed)
    return q.order_by(DriftInterventionEvent.start_at.desc()).limit(limit).all()
