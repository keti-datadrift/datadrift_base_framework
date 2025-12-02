from fastapi import APIRouter, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Dataset
from ..services.dataset_service import create_dataset, delete_dataset

from app.schemas import DatasetSchema

    
router = APIRouter(prefix="/datasets", tags=["datasets"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_dataset(file: UploadFile, db: Session = Depends(get_db)):
    dataset = create_dataset(db, file)
    return dataset


@router.get("/", response_model=list[DatasetSchema])
def list_datasets(db: Session = Depends(get_db)):
    items = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    return items  # Pydantic이 자동 변환 + sanitize


@router.delete("/{dataset_id}")
def remove_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """
    데이터셋과 관련된 모든 데이터를 삭제합니다.
    - 관련 EDA 결과
    - 관련 Drift 결과 (base 또는 target으로 사용된 경우)
    - 파일 시스템의 데이터셋 폴더
    - Dataset DB 레코드
    """
    result = delete_dataset(db, dataset_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result
