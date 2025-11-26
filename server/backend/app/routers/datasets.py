from fastapi import APIRouter, UploadFile, Depends
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Dataset
from ..services.dataset_service import create_dataset

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

@router.get("/")
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).order_by(Dataset.created_at.desc()).all()