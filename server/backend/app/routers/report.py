import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Dataset
from app.services.eda_service import run_eda
from app.reports.report_service import generate_eda_report, generate_zip_eda_report

router = APIRouter(prefix="/report", tags=["report"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/eda/{dataset_id}")
def generate_eda_route(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # ZIP이면 ZIP 전용 리포트
    if ds.type == "zip":
        eda = run_eda(ds.dvc_path, "zip")
        paths = generate_zip_eda_report(ds, eda)
    else:
        eda = run_eda(ds.dvc_path, ds.type or "csv")
        # 간단 예시: rows/cols는 eda.shape에서 가져온다고 가정
        rows, cols = (0, 0)
        if "shape" in eda:
            rows, cols = eda["shape"]
        paths = generate_eda_report(
            {
                "id": ds.id,
                "name": ds.name,
                "rows": rows,
                "cols": cols,
                "missing": eda.get("missing_rate", {}),
                "summary": eda.get("summary", {}),
            }
        )

    return {"html": paths["html"], "pdf": paths["pdf"]}


@router.get("/download")
def download_report(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, filename=os.path.basename(path))