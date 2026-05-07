from sqlalchemy import Column, String, Integer, Float, DateTime, JSON
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