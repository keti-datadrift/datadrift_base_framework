from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Dataset
from app.services.eda_service import run_eda


router = APIRouter(prefix="/eda", tags=["eda"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{dataset_id}")
def eda(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return run_eda(
        file_path=ds.dvc_path,
        dtype=ds.type.lower() if ds.type else "csv"
    )

from fastapi import BackgroundTasks

def _run_eda_background(dataset_id: str):
    # 향후 Celery/RQ로 교체하기 쉽도록 별도 함수로 분리.
    from app.database import SessionLocal
    from app.models import Dataset
    from app.services.eda_service import run_eda as _run_eda

    db = SessionLocal()
    try:
        ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if ds:
            _ = _run_eda(ds.dvc_path, ds.type or "unknown")
    finally:
        db.close()

@router.post("/async/{dataset_id}")
def eda_async(dataset_id: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    # 단순히 큐에 넣고 바로 응답하는 형태의 비동기 EDA 실행.
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    background.add_task(_run_eda_background, dataset_id)
    return {"status": "queued"}
