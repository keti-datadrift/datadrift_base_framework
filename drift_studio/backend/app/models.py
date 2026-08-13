from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from .database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String)              # csv / text / image / video ...
    size = Column(Integer)             # 파일 크기(옵션)
    rows = Column(Integer)
    cols = Column(Integer)
    missing_rate = Column(JSON)        # {col: rate}
    preview = Column(JSON)             # 예: head(5)
    dvc_path = Column(String)          # data/.. 경로
    version = Column(String)           # DVC 버전 태그
    created_at = Column(DateTime, server_default=func.now())


class EDAResult(Base):
    __tablename__ = "eda_results"

    id = Column(String, primary_key=True)
    dataset_id = Column(String, index=True)
    summary = Column(JSON)
    missing_rate = Column(JSON)
    stats = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now())


class DriftResult(Base):
    __tablename__ = "drift_results"

    id = Column(String, primary_key=True)
    base_id = Column(String, index=True)
    target_id = Column(String, index=True)
    summary = Column(JSON)
    feature_drift = Column(JSON)
    overall = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class AnalysisTask(Base):
    """분석 작업 상태 추적 테이블"""
    __tablename__ = "analysis_tasks"

    id = Column(String, primary_key=True)
    dataset_id = Column(String, index=True)
    target_id = Column(String, nullable=True, index=True)  # drift 분석용
    task_type = Column(String)  # eda, image_analysis, clustering, drift
    status = Column(String, default="pending")  # pending/in_progress/completed/failed
    progress = Column(Float, default=0.0)  # 0.0 ~ 1.0
    message = Column(String, nullable=True)
    error = Column(String, nullable=True)
    task_metadata = Column(JSON, nullable=True)  # ETA, 처리 파일 수 등
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


# ── Field Agent Hub (Phase B — 3-project integration) ──────────────


class FieldAgent(Base):
    """현장 앱 등록 (e.g. keti-veritas instances)."""
    __tablename__ = "field_agents"

    id = Column(String, primary_key=True)           # UUID
    app_id = Column(String, unique=True, index=True) # e.g. "keti-veritas-prod-01"
    app_type = Column(String, nullable=True)         # e.g. "video_forensics"
    display_name = Column(String, nullable=True)
    api_base_url = Column(String, nullable=True)     # e.g. "http://192.168.1.100:8010"
    api_key_hash = Column(String, nullable=True)     # SHA-256 of agent's API key
    status = Column(String, default="active")        # active / inactive / degraded
    capabilities = Column(JSON, nullable=True)       # ["drift_report", "model_receive", ...]
    registered_models = Column(JSON, nullable=True)  # [{name, type, version}, ...]
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FieldDriftReport(Base):
    """현장에서 수신한 drift report."""
    __tablename__ = "field_drift_reports"

    id = Column(String, primary_key=True)            # UUID
    agent_id = Column(String, index=True)             # FK → field_agents.id
    report_json = Column(JSON, nullable=False)        # Full DriftReport payload
    severity = Column(String, index=True)             # low / medium / high
    model_name = Column(String, nullable=True)
    drift_overall = Column(Float, nullable=True)      # drift.scores.overall
    status = Column(String, default="received")       # received / analyzing / action_taken / archived
    action_taken = Column(JSON, nullable=True)        # Decision engine result
    created_at = Column(DateTime, server_default=func.now())


class TrainerAgent(Base):
    """학습 전문 에이전트 등록 (e.g. alpr training server)."""
    __tablename__ = "trainer_agents"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, index=True)     # e.g. "alpr-trainer"
    trainer_type = Column(String, nullable=True)        # e.g. "alpr", "yolo", "generic"
    api_base_url = Column(String, nullable=False)       # e.g. "http://alpr:8090"
    api_key_hash = Column(String, nullable=True)
    status = Column(String, default="active")           # active / inactive / busy
    capabilities = Column(JSON, nullable=True)          # ["recognizer", "detector"]
    created_at = Column(DateTime, server_default=func.now())
    last_heartbeat = Column(DateTime, nullable=True)


class TrainingJob(Base):
    """dd가 트리거한 학습 작업 추적."""
    __tablename__ = "training_jobs"

    id = Column(String, primary_key=True)
    trainer_id = Column(String, index=True)             # FK → trainer_agents.id
    drift_report_id = Column(String, nullable=True)     # FK → field_drift_reports.id
    field_agent_id = Column(String, nullable=True)      # 학습 요청의 원인이 된 필드 에이전트
    command_json = Column(JSON, nullable=False)          # TrainingCommand payload
    status = Column(String, default="pending")           # pending / running / completed / failed
    progress = Column(Float, default=0.0)
    result_json = Column(JSON, nullable=True)            # ModelPackage or error
    error = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


# ── Model Promotion Gate (챔피언/챌린저 검증 + 승인, context_workplace/
# drift_tool_analysis.md 5부·12부) ──────────────────────────────────────
#
# 이전에는 training_orchestrator.receive_result()가 외부 트레이너가 자체
# 보고한 acceptance.gate_passed만 믿고 autonomous_loop.on_training_completed
# 가 바로 deploy_to_all_agents()를 호출했다 — 독립 검증도, "지금 뭐가
# 배포돼 있는지"에 대한 영속 기록도 없었다(model_deployment_service.
# _get_current_version()가 항상 None을 반환하는 스텁이었던 이유).
# 이 테이블이 그 챔피언 이력을 실제로 기록한다.
class ModelPromotion(Base):
    """재학습된 챌린저 모델을 배포하기 전의 검증·승인 기록."""
    __tablename__ = "model_promotions"

    id = Column(String, primary_key=True)
    training_job_id = Column(String, index=True)          # FK → training_jobs.id (챌린저)
    model_name = Column(String, index=True)
    field_agent_id = Column(String, nullable=True)
    champion_training_job_id = Column(String, nullable=True)  # FK → training_jobs.id (직전 배포된 모델)
    champion_metrics = Column(JSON, nullable=True)         # 직전 배포 시점의 acceptance 지표
    challenger_metrics = Column(JSON, nullable=True)       # 이번 job의 acceptance 지표
    comparison = Column(JSON, nullable=True)               # {common_metrics, deltas, note}
    # pending_approval / auto_approved / approved / rejected / deployed
    status = Column(String, default="pending_approval", index=True)
    decided_by = Column(String, nullable=True)
    decision_reason = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    decided_at = Column(DateTime, nullable=True)


# ── Drift Intervention Events (DriftDecisionEngine 보정, context_workplace/
# drift_tool_analysis.md 3부·12부, Round 36) ────────────────────────────
#
# DriftDecisionEngine은 필드 에이전트가 자체 보고한 severity 문자열을
# 검증 없이 그대로 신뢰한다 — ModelPromotion이 고친 gate_passed 블라인드 신뢰
# 문제와 같은 모양이 파이프라인 반대쪽 끝(재학습 결과가 아니라 드리프트
# 판정 자체)에도 있다. 이 테이블은 ddoc_plugin_reference_engine/
# event_store.py의 intervention_log와 같은 개념을 (model_name,
# field_agent_id) 스코프로 재구성한 것 — 그 플러그인의 로컬 YAML은 이
# 백엔드 프로세스가 읽을 수 있는 게 아니라서 own 테이블이 필요했다.
class DriftInterventionEvent(Base):
    """사람이 등록한 '이미 알려진 의도적/일시적 변화' 구간."""
    __tablename__ = "drift_intervention_events"

    id = Column(String, primary_key=True)
    model_name = Column(String, nullable=False, index=True)
    field_agent_id = Column(String, nullable=True, index=True)  # None = 이 모델의 모든 에이전트
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)  # None = 아직 진행 중
    description = Column(String, nullable=True)
    confirmed = Column(Boolean, default=True)
    proposed_by = Column(String, default="human")
    created_at = Column(DateTime, server_default=func.now())