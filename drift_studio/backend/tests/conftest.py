"""Backend has no existing test suite (confirmed: no tests/ directory
anywhere under drift_studio/backend/ before this file -- the extensive
test_server*.py/test_plugin_*.py suite lives under drift_studio/ddoc/tests/
and covers the CLI, not this FastAPI app). This conftest is scoped to what
Round 35 (promotion gate) needs: an isolated in-memory DB per test, not a
full app fixture.
"""
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DD_ARTIFACTS_DIR", "/tmp/dd_test_artifacts")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
