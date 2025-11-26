from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Dataset
from ..reports.report_service import generate_eda_report
from ..services.eda_service import run_eda

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

    # EDA 실행
    eda_result = run_eda(ds.dvc_path)

    report_info = generate_eda_report({
        "id": ds.id,
        "name": ds.name,
        "rows": eda_result["shape"][0],
        "cols": eda_result["shape"][1],
        "missing": eda_result["missing_rate"],
        "summary": eda_result["summary"],
    })

    return {
        "html": report_info["html"],
        "pdf": report_info["pdf"]
    }


@router.get("/download")
def download_report(path: str):
    """파일 다운로드 API"""
    return FileResponse(path, filename=path.split("/")[-1])