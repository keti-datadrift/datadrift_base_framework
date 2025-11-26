from fastapi import APIRouter, UploadFile, Depends
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..services.dataset_service import create_dataset
from ..models import Dataset

router = APIRouter(prefix="/datasets")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
def upload_dataset(file: UploadFile, db: Session = Depends(get_db)):
    dataset = create_dataset(db, file)
    return dataset

@router.get("/")
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).all()