import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Dataset
from app.reports.report_service import generate_eda_report
from app.services.eda_service import run_eda


router = APIRouter(prefix="/report", tags=["report"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/eda/{dataset_id}")
def generate_eda(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    eda_result = run_eda(ds.dvc_path, ds.type or "unknown")

    report_info = generate_eda_report(
        {
            "id": ds.id,
            "name": ds.name,
            "rows": eda_result["shape"][0],
            "cols": eda_result["shape"][1],
            "missing": eda_result.get("missing_rate", {}),
            "summary": eda_result.get("summary", {}),
        }
    )

    return report_info


@router.get("/download")
def download_report(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path, filename=os.path.basename(path))
