"""Champion/challenger promotion gate (Round 35, drift_tool_analysis.md
5부/12부). Formalizes the ad-hoc verification run during implementation.
"""
from app.models import TrainingJob
from app.services import promotion_gate_service as gate


def _make_job(job_id, *, model_name, accuracy, field_agent_id="agent1", gate_passed=True):
    return TrainingJob(
        id=job_id, trainer_id="t1", field_agent_id=field_agent_id,
        command_json={"training": {"pipeline": "alpr"}},
        status="completed",
        result_json={"acceptance": {"gate_passed": gate_passed, "accuracy": accuracy},
                     "model": {"name": model_name}},
    )


def test_first_deployment_auto_approves(db):
    job = _make_job("job1", model_name="alpr-recognizer", accuracy=0.91)
    db.add(job)
    db.commit()

    promotion = gate.evaluate_promotion(db, job, model_name="alpr-recognizer")

    assert promotion.status == "auto_approved"
    assert promotion.champion_training_job_id is None
    assert "첫 배포" in promotion.decision_reason


def test_second_deployment_requires_approval_with_comparison(db):
    champion_job = _make_job("job1", model_name="alpr-recognizer", accuracy=0.91)
    db.add(champion_job)
    db.commit()
    champion_promotion = gate.evaluate_promotion(db, champion_job, model_name="alpr-recognizer")
    gate.mark_deployed(db, champion_promotion.id)

    challenger_job = _make_job("job2", model_name="alpr-recognizer", accuracy=0.95)
    db.add(challenger_job)
    db.commit()
    promotion = gate.evaluate_promotion(db, challenger_job, model_name="alpr-recognizer")

    assert promotion.status == "pending_approval"
    assert promotion.champion_training_job_id == "job1"
    assert promotion.comparison["deltas"]["accuracy"] == 0.04
    assert "gate_passed" not in promotion.comparison["deltas"], (
        "gate_passed is a control-flow field already checked upstream, not a metric to diff"
    )


def test_pending_promotion_shows_up_in_list_pending(db):
    champion_job = _make_job("job1", model_name="m", accuracy=0.9)
    db.add(champion_job)
    db.commit()
    gate.mark_deployed(db, gate.evaluate_promotion(db, champion_job, model_name="m").id)

    challenger_job = _make_job("job2", model_name="m", accuracy=0.92)
    db.add(challenger_job)
    db.commit()
    promotion = gate.evaluate_promotion(db, challenger_job, model_name="m")

    pending = gate.list_pending(db)
    assert [p.id for p in pending] == [promotion.id]


def test_approve_transitions_status_and_records_decider(db):
    champion_job = _make_job("job1", model_name="m", accuracy=0.9)
    db.add(champion_job)
    db.commit()
    gate.mark_deployed(db, gate.evaluate_promotion(db, champion_job, model_name="m").id)

    challenger_job = _make_job("job2", model_name="m", accuracy=0.92)
    db.add(challenger_job)
    db.commit()
    promotion = gate.evaluate_promotion(db, challenger_job, model_name="m")

    approved = gate.approve_promotion(db, promotion.id, approved_by="reviewer1", reason="looks good")
    assert approved.status == "approved"
    assert approved.decided_by == "reviewer1"
    assert approved.decided_at is not None


def test_reject_transitions_status_and_requires_reason(db):
    champion_job = _make_job("job1", model_name="m", accuracy=0.9)
    db.add(champion_job)
    db.commit()
    gate.mark_deployed(db, gate.evaluate_promotion(db, champion_job, model_name="m").id)

    challenger_job = _make_job("job2", model_name="m", accuracy=0.5)  # 실제로 더 나쁨
    db.add(challenger_job)
    db.commit()
    promotion = gate.evaluate_promotion(db, challenger_job, model_name="m")

    rejected = gate.reject_promotion(db, promotion.id, rejected_by="reviewer1", reason="accuracy regressed")
    assert rejected.status == "rejected"
    assert rejected.decision_reason == "accuracy regressed"


def test_cannot_approve_already_decided_promotion(db):
    champion_job = _make_job("job1", model_name="m", accuracy=0.9)
    db.add(champion_job)
    db.commit()
    gate.mark_deployed(db, gate.evaluate_promotion(db, champion_job, model_name="m").id)

    challenger_job = _make_job("job2", model_name="m", accuracy=0.92)
    db.add(challenger_job)
    db.commit()
    promotion = gate.evaluate_promotion(db, challenger_job, model_name="m")

    gate.approve_promotion(db, promotion.id, approved_by="reviewer1")
    second_attempt = gate.approve_promotion(db, promotion.id, approved_by="someone_else")
    assert second_attempt is None, "approving an already-decided promotion should be a no-op, not silently re-approve"


def test_different_field_agents_get_independent_champion_history(db):
    """레짐/개입 로그의 series 구분과 같은 원칙 -- 배포 대상(field_agent)이
    다르면 서로 다른 챔피언 이력을 가져야 한다."""
    job_agent1 = _make_job("job1", model_name="m", accuracy=0.9, field_agent_id="agent1")
    db.add(job_agent1)
    db.commit()
    gate.mark_deployed(db, gate.evaluate_promotion(db, job_agent1, model_name="m").id)

    job_agent2 = _make_job("job2", model_name="m", accuracy=0.5, field_agent_id="agent2")
    db.add(job_agent2)
    db.commit()
    promotion = gate.evaluate_promotion(db, job_agent2, model_name="m")

    assert promotion.status == "auto_approved", "agent2에게는 아직 챔피언이 없으므로 첫 배포로 취급"
