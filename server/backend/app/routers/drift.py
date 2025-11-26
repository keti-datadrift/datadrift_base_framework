from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Dataset
from app.services.drift_service import run_drift

router = APIRouter(prefix="/drift", tags=["drift"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DriftRequest(BaseModel):
    base_id: str
    target_id: str

@router.post("/")
def drift(req: DriftRequest, db: Session = Depends(get_db)):
    base = db.query(Dataset).filter(Dataset.id == req.base_id).first()
    target = db.query(Dataset).filter(Dataset.id == req.target_id).first()

    if not base or not target:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return run_drift(base.dvc_path, target.dvc_path)

@router.post("/v2")
def drift_v2(req: DriftRequest, db: Session = Depends(get_db)):
    base = db.query(Dataset).filter(Dataset.id == req.base_id).first()
    target = db.query(Dataset).filter(Dataset.id == req.target_id).first()

    if not base or not target:
        raise HTTPException(status_code=404, detail="Dataset not found")

    core = run_drift(base.dvc_path, target.dvc_path)
    core["meta"] = {
        "base": {"id": base.id, "name": base.name, "dvc_path": base.dvc_path},
        "target": {"id": target.id, "name": target.name, "dvc_path": target.dvc_path},
    }
    core["version"] = "v2"
    return core
