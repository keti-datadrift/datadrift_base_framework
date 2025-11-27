from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Dataset
from app.services.drift_service import run_drift

router = APIRouter(prefix="/drift", tags=["drift"])


# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Request Body
class DriftRequest(BaseModel):
    base_id: str
    target_id: str


# -------------------------------
# COMMON Response Wrapper
# -------------------------------
def wrap_drift_response(base: Dataset, target: Dataset, result: dict, version: str):
    """
    drift_service.py의 결과(result)를 안정적인 JSON 형태로 감싸주는 공통 포맷
    """

    return {
        "version": version,
        "meta": {
            "base": {
                "id": base.id,
                "name": base.name,
                "type": base.type,
                "dvc_path": base.dvc_path,
            },
            "target": {
                "id": target.id,
                "name": target.name,
                "type": target.type,
                "dvc_path": target.dvc_path,
            },
        },
        "result": result,   # drift_service.py 의 핵심 분석값
    }


# ============================================================
# Drift V1
# ============================================================

@router.post("/")
def drift(req: DriftRequest, db: Session = Depends(get_db)):
    base = db.query(Dataset).filter(Dataset.id == req.base_id).first()
    target = db.query(Dataset).filter(Dataset.id == req.target_id).first()

    if not base or not target:
        raise HTTPException(status_code=404, detail="Dataset not found")

    result = run_drift(base.dvc_path, target.dvc_path)

    return wrap_drift_response(base, target, result, version="v1")


# ============================================================
# Drift V2 (확장 포맷)
# ============================================================

@router.post("/v2")
def drift_v2(req: DriftRequest, db: Session = Depends(get_db)):
    base = db.query(Dataset).filter(Dataset.id == req.base_id).first()
    target = db.query(Dataset).filter(Dataset.id == req.target_id).first()

    if not base or not target:
        raise HTTPException(status_code=404, detail="Dataset not found")

    result = run_drift(base.dvc_path, target.dvc_path)

    return wrap_drift_response(base, target, result, version="v2")