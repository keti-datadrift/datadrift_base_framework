"""DriftDecisionEngine 이벤트 보정 레이어 (Round 36, drift_tool_analysis.md
3부/12부). promotion_gate_service의 자체보고-블라인드-신뢰-금지 원칙을
파이프라인 반대쪽 끝(드리프트 판정 자체)에 적용한 것을 검증한다.
"""
import uuid
from datetime import datetime, timedelta

from app.models import DriftInterventionEvent, FieldDriftReport, TrainerAgent
from app.services import drift_corroboration_service as corr


def _make_trainer(db, *, name="trainer1", trainer_type="generic"):
    trainer = TrainerAgent(
        id=str(uuid.uuid4()), name=name, trainer_type=trainer_type,
        api_base_url="http://trainer.local", status="active",
    )
    db.add(trainer)
    db.commit()
    return trainer


def _make_report(db, *, severity, model_name="model-x", agent_id="agent1", created_at=None):
    report = FieldDriftReport(
        id=str(uuid.uuid4()), agent_id=agent_id, report_json={}, severity=severity,
        model_name=model_name, status="received", created_at=created_at or datetime.utcnow(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _make_event(db, *, model_name="model-x", field_agent_id=None, start_at, end_at=None,
                 confirmed=True, description="known intervention"):
    event = DriftInterventionEvent(
        id=str(uuid.uuid4()), model_name=model_name, field_agent_id=field_agent_id,
        start_at=start_at, end_at=end_at, description=description, confirmed=confirmed,
    )
    db.add(event)
    db.commit()
    return event


def test_no_event_leaves_decision_unaffected(db):
    _make_trainer(db)
    report = _make_report(db, severity="high")

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "retrain"
    assert decision.trainer_name is not None
    assert decision.corroboration == {"checked": True, "matched_events": []}


def test_confirmed_overlapping_event_downgrades_retrain_to_alert(db):
    _make_trainer(db)
    now = datetime.utcnow()
    report = _make_report(db, severity="high", created_at=now)
    _make_event(db, start_at=now - timedelta(days=1), end_at=now + timedelta(days=1),
                confirmed=True, description="카메라 캘리브레이션 재조정")

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "alert"
    assert decision.original_action == "retrain"
    assert decision.trainer_name is None
    matched = decision.corroboration["matched_events"]
    assert len(matched) == 1
    assert matched[0]["confirmed"] is True
    assert matched[0]["description"] == "카메라 캘리브레이션 재조정"


def test_unconfirmed_candidate_event_does_not_affect_decision(db):
    _make_trainer(db)
    now = datetime.utcnow()
    report = _make_report(db, severity="high", created_at=now)
    _make_event(db, start_at=now - timedelta(days=1), end_at=now + timedelta(days=1), confirmed=False)

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "retrain", "미승인 후보는 결정에 영향을 주면 안 됨"
    assert decision.trainer_name is not None
    matched = decision.corroboration["matched_events"]
    assert len(matched) == 1, "숨기지는 않음 -- 참고용으로는 보여줌"
    assert matched[0]["confirmed"] is False


def test_event_for_different_model_does_not_match(db):
    _make_trainer(db)
    now = datetime.utcnow()
    report = _make_report(db, severity="high", model_name="model-x", created_at=now)
    _make_event(db, model_name="model-y", start_at=now - timedelta(days=1), end_at=now + timedelta(days=1))

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "retrain"
    assert decision.corroboration["matched_events"] == []


def test_event_for_different_field_agent_does_not_match(db):
    _make_trainer(db)
    now = datetime.utcnow()
    report = _make_report(db, severity="high", agent_id="agent1", created_at=now)
    _make_event(db, field_agent_id="agent2", start_at=now - timedelta(days=1), end_at=now + timedelta(days=1))

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "retrain"
    assert decision.corroboration["matched_events"] == []


def test_wildcard_field_agent_id_matches_any_agent(db):
    """field_agent_id=None으로 등록하면 이 모델을 쓰는 모든 에이전트에 적용."""
    _make_trainer(db)
    now = datetime.utcnow()
    report = _make_report(db, severity="high", agent_id="agent-whichever", created_at=now)
    _make_event(db, field_agent_id=None, start_at=now - timedelta(days=1), end_at=now + timedelta(days=1))

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "alert"
    assert len(decision.corroboration["matched_events"]) == 1


def test_open_ended_event_still_matches_in_progress_report(db):
    _make_trainer(db)
    now = datetime.utcnow()
    report = _make_report(db, severity="high", created_at=now)
    _make_event(db, start_at=now - timedelta(days=5), end_at=None)

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "alert"
    assert len(decision.corroboration["matched_events"]) == 1


def test_event_outside_time_window_does_not_match(db):
    _make_trainer(db)
    now = datetime.utcnow()
    report = _make_report(db, severity="high", created_at=now)
    _make_event(db, start_at=now - timedelta(days=10), end_at=now - timedelta(days=5))

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "retrain"
    assert decision.corroboration["matched_events"] == []


def test_uses_report_created_at_not_wall_clock_now(db):
    """평가 시점의 wall-clock now가 아니라 report.created_at 기준으로 겹침을
    판정해야 한다 -- 반대로 짜면(now 기준) 이 테스트만 실패한다."""
    _make_trainer(db)
    past = datetime.utcnow() - timedelta(days=40)
    report = _make_report(db, severity="high", created_at=past)
    _make_event(db, start_at=past - timedelta(days=1), end_at=past + timedelta(days=1))

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "alert"
    assert len(decision.corroboration["matched_events"]) == 1


def test_escalated_medium_alert_without_trainer_gets_corroboration_context(db):
    """트레이너가 하나도 없어 RETRAIN 대신 ALERT가 나오는 에스컬레이션
    경로(코드상 평범한 medium ALERT와 완전히 같은 모양)에서도 겹치는
    이벤트가 있으면 matched_events가 채워져야 한다."""
    now = datetime.utcnow()
    model_name, agent_id = "model-x", "agent1"
    _make_report(db, severity="medium", model_name=model_name, agent_id=agent_id,
                 created_at=now - timedelta(hours=2))
    _make_report(db, severity="medium", model_name=model_name, agent_id=agent_id,
                 created_at=now - timedelta(hours=1))
    report = _make_report(db, severity="medium", model_name=model_name, agent_id=agent_id, created_at=now)
    _make_event(db, model_name=model_name, start_at=now - timedelta(days=1), end_at=now + timedelta(days=1))

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "alert", "트레이너가 없으므로 원래도 ALERT"
    assert len(decision.corroboration["matched_events"]) == 1, (
        "에스컬레이션 경로에서도 겹치는 이벤트는 채워져야 함"
    )


def test_low_severity_never_checks_corroboration(db):
    """OBSERVE는 애초에 재학습/에스컬레이션 경로가 아니므로 이벤트 조회 자체를
    안 해야 한다(checked=False로 남음)."""
    now = datetime.utcnow()
    report = _make_report(db, severity="low", created_at=now)
    _make_event(db, start_at=now - timedelta(days=1), end_at=now + timedelta(days=1))

    decision = corr.evaluate_corroborated(db, report)

    assert decision.action == "observe"
    assert decision.corroboration == {"checked": False, "matched_events": []}
