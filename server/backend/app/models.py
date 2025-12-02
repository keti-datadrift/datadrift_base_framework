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