from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

DATABASE_URL = "sqlite:///./db.sqlite3"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    # 연결 풀 설정 - 동시 작업 지원
    poolclass=QueuePool,
    pool_size=10,        # 기본 연결 수 (기존 5 → 10)
    max_overflow=20,     # 추가 허용 연결 수 (기존 10 → 20)
    pool_timeout=60,     # 연결 대기 타임아웃 (기존 30 → 60초)
    pool_recycle=3600,   # 연결 재사용 주기 (1시간)
    pool_pre_ping=True,  # 연결 유효성 사전 검사
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()