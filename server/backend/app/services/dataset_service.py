import uuid
import os
import pandas as pd
from sqlalchemy.orm import Session
from ..models import Dataset
from .dvc_service import dvc_add_file

def create_dataset(db: Session, uploaded_file) -> Dataset:
    file_path, version_info = dvc_add_file(uploaded_file)

    size_value = os.path.getsize(file_path)
    
    # CSV 기준 토이 구현
    _, ext = os.path.splitext(uploaded_file.filename)
    dtype = "csv"
    if ext.lower() in [".png", ".jpg", ".jpeg"]:
        dtype = "image"
    elif ext.lower() in [".mp4", ".avi", ".mov"]:
        dtype = "video"
    elif ext.lower() in [".txt", ".md"]:
        dtype = "text"

    rows = 0
    cols = 0
    missing_rate = {}
    preview = {}

    if dtype == "csv":
        df = pd.read_csv(file_path)
        rows, cols = df.shape
        missing_rate = df.isna().mean().to_dict()
        preview = {"head": df.head(5).to_dict(orient="records")}

    dataset = Dataset(
        id=str(uuid.uuid4()),
        name=uploaded_file.filename,
        type=dtype,
        #size=len(content) if dtype != "csv" else rows,
        size=size_value,
        rows=rows,
        cols=cols,
        missing_rate=missing_rate,
        preview=preview,
        dvc_path=file_path,
        version="v1",   # 간단히 고정, 추후 개선 가능
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset