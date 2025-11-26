from fastapi import APIRouter, UploadFile
from app.services.dataset_store import store

router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.post("/upload")
async def upload_dataset(file: UploadFile):
    ds_id = store.add_dataset(file)
    return {"dataset_id": ds_id, "name": file.filename}

@router.get("/")
async def list_datasets():
    return store.list_datasets()