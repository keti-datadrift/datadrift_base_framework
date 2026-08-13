"""Champion/challenger promotion gate.

context_workplace/drift_tool_analysis.md 5부(섀도 재학습 + 챔피언/챌린저
검증)와 12부(인과추론 관점의 자기비판 -- "설명됨"이 아니라 "설명 후보",
자동화된 주장을 과신하지 말 것)를 이 백엔드에 실제로 적용한 것.

발견한 문제(직접 소스를 읽어 확인): `training_orchestrator.receive_result()`
는 외부 트레이너가 자체 보고한 `result["acceptance"]["gate_passed"]` 불리언만
보고 job.status를 "completed"로 바꾼다. `autonomous_loop.on_training_completed()`
는 `DD_AUTO_DEPLOY=true`일 때 그 값만 확인하고 바로
`model_deployment_service.deploy_to_all_agents()`를 호출한다 -- 독립 검증도,
"지금 어떤 모델이 배포돼 있는지"에 대한 영속 기록도 없다
(`model_deployment_service._get_current_version()`는 항상 `None`을 반환하는
스텁). 이 모듈이 그 사이에 게이트를 하나 끼워 넣는다.

설계 원칙 (첫 배포 이후부터 적용):
- 비교할 챔피언이 아직 없으면(이 model_name·field_agent 조합의 첫 배포)
  자동 승인한다 -- 비교 대상이 없으므로 막을 이유가 없다.
- 챔피언이 이미 있으면, 외부 트레이너가 보고한 gate_passed를 다시 검증하지
  않고 **항상 사람/에이전트 승인을 요구한다**. 외부 트레이너의 acceptance
  페이로드 스키마를 이 저장소 코드에서 확인할 수 없어(다른 시스템), 어떤
  지표가 "높을수록 좋다"인지 안전하게 자동 판정할 근거가 부족하기 때문이다
  -- 비교 가능한 공통 지표가 있으면 참고용으로 함께 보여주기만 한다.
- 수동 배포(`POST /deployment/deploy`, 사람이 명시적으로 호출)는 그 호출
  자체가 이미 승인이므로 게이트를 막지 않는다 -- 다만 같은
  ModelPromotion 이력에 챔피언으로 기록해서, 다음 비교의 근거가 되게 한다.
  자동 루프(`DD_AUTO_DEPLOY=true`, 사람이 전혀 개입하지 않는 경로)만 이
  게이트로 막는다.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import ModelPromotion, TrainingJob

logger = logging.getLogger(__name__)


def _extract_metrics(job: TrainingJob) -> dict:
    result = job.result_json or {}
    return result.get("acceptance", {}) or {}


_NON_METRIC_KEYS = {"gate_passed"}  # 제어흐름 필드 -- 별도로 이미 확인됨, diff 대상 아님


def _compare_metrics(champion: dict, challenger: dict) -> dict:
    """참고용 비교. common 키의 산술 차이만 보여주고, 어느 방향이 '좋음'인지는
    판단하지 않는다 -- 외부 스키마를 신뢰할 수 없으므로 사람이 직접 본다."""
    common = sorted((set(champion) & set(challenger)) - _NON_METRIC_KEYS)
    deltas = {}
    for key in common:
        try:
            deltas[key] = round(float(challenger[key]) - float(champion[key]), 6)
        except (TypeError, ValueError):
            continue
    return {
        "common_metrics": common,
        "deltas": deltas,
        "note": (
            "어느 방향이 개선인지는 이 게이트가 판단하지 않습니다 -- "
            "승인자가 직접 확인하세요 (12부: 자동 귀속을 과신하지 않는다)."
        ),
    }


def find_current_champion(db: Session, model_name: str, field_agent_id: str | None) -> ModelPromotion | None:
    """이 (model_name, field_agent_id) 조합에 마지막으로 배포된 프로모션."""
    q = db.query(ModelPromotion).filter(
        ModelPromotion.model_name == model_name,
        ModelPromotion.status == "deployed",
    )
    if field_agent_id:
        q = q.filter(ModelPromotion.field_agent_id == field_agent_id)
    return q.order_by(ModelPromotion.decided_at.desc()).first()


def evaluate_promotion(db: Session, job: TrainingJob, *, model_name: str) -> ModelPromotion:
    """훈련이 끝난 challenger job에 대해 프로모션 레코드를 만들고
    auto_approved 또는 pending_approval 상태로 반환한다."""
    challenger_metrics = _extract_metrics(job)
    champion = find_current_champion(db, model_name, job.field_agent_id)

    promotion = ModelPromotion(
        id=str(uuid.uuid4()),
        training_job_id=job.id,
        model_name=model_name,
        field_agent_id=job.field_agent_id,
        challenger_metrics=challenger_metrics,
    )

    if champion is None:
        promotion.status = "auto_approved"
        promotion.decided_by = "system:bootstrap"
        promotion.decision_reason = f"{model_name}의 첫 배포 -- 비교할 챔피언이 없어 자동 승인"
        promotion.decided_at = datetime.utcnow()
    else:
        promotion.champion_training_job_id = champion.training_job_id
        promotion.champion_metrics = champion.challenger_metrics  # 그때는 challenger, 지금은 champion
        promotion.comparison = _compare_metrics(champion.challenger_metrics or {}, challenger_metrics)
        promotion.status = "pending_approval"
        promotion.decision_reason = (
            f"기존 챔피언(job={champion.training_job_id}) 대비 독립 승인 필요"
        )

    db.add(promotion)
    db.commit()
    db.refresh(promotion)
    logger.info(
        "[PromotionGate] job=%s model=%s -> %s (%s)",
        job.id, model_name, promotion.status, promotion.decision_reason,
    )
    return promotion


def record_manual_deployment(db: Session, job: TrainingJob, *, model_name: str, decided_by: str = "manual") -> ModelPromotion:
    """사람이 명시적으로 /deployment/deploy를 호출한 경우 -- 그 호출 자체가
    승인이므로 게이트로 막지 않되, 다음 비교를 위해 챔피언으로 기록한다."""
    promotion = ModelPromotion(
        id=str(uuid.uuid4()),
        training_job_id=job.id,
        model_name=model_name,
        field_agent_id=job.field_agent_id,
        challenger_metrics=_extract_metrics(job),
        status="deployed",
        decided_by=decided_by,
        decision_reason="수동 배포 호출 자체를 승인으로 간주",
        decided_at=datetime.utcnow(),
    )
    db.add(promotion)
    db.commit()
    db.refresh(promotion)
    return promotion


def approve_promotion(db: Session, promotion_id: str, *, approved_by: str, reason: str | None = None) -> ModelPromotion | None:
    promotion = db.query(ModelPromotion).filter(ModelPromotion.id == promotion_id).first()
    if promotion is None or promotion.status != "pending_approval":
        return None
    promotion.status = "approved"
    promotion.decided_by = approved_by
    promotion.decision_reason = reason or "승인됨"
    promotion.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(promotion)
    return promotion


def reject_promotion(db: Session, promotion_id: str, *, rejected_by: str, reason: str) -> ModelPromotion | None:
    promotion = db.query(ModelPromotion).filter(ModelPromotion.id == promotion_id).first()
    if promotion is None or promotion.status != "pending_approval":
        return None
    promotion.status = "rejected"
    promotion.decided_by = rejected_by
    promotion.decision_reason = reason
    promotion.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(promotion)
    return promotion


def mark_deployed(db: Session, promotion_id: str) -> ModelPromotion | None:
    """실제 deploy_to_all_agents() 호출이 성공한 뒤, 이 프로모션을 새 챔피언으로 확정."""
    promotion = db.query(ModelPromotion).filter(ModelPromotion.id == promotion_id).first()
    if promotion is None:
        return None
    promotion.status = "deployed"
    if not promotion.decided_at:
        promotion.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(promotion)
    return promotion


def list_pending(db: Session, limit: int = 50) -> list[ModelPromotion]:
    return (
        db.query(ModelPromotion)
        .filter(ModelPromotion.status == "pending_approval")
        .order_by(ModelPromotion.created_at.desc())
        .limit(limit)
        .all()
    )
