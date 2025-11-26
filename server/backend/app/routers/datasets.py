from fastapi import APIRouter, UploadFile, Depends
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Dataset
from ..services.dataset_service import create_dataset

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
