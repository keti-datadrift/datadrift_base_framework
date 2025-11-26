import os
import uuid
from typing import Optional, Dict, Any

import pandas as pd
from sqlalchemy.orm import Session
from PIL import Image

from app.models import Dataset
from app.services.dvc_service import dvc_add_file
from app.utils.json_sanitize import clean_json_value


# -----------------------------------------------
# 썸네일 생성 (현재는 이미지에만 적용)
# -----------------------------------------------
def create_thumbnail(dtype: str, file_path: str) -> Optional[str]:
    """이미지 타입에 대해 128x128 썸네일 생성. 실패 시 None 반환."""
    if dtype != "image":
        return None
    try:
        img = Image.open(file_path).convert("RGB")
        img.thumbnail((128, 128))
        thumb_path = f"{file_path}_thumbnail.jpg"
        img.save(thumb_path, format="JPEG")
        return thumb_path
    except Exception:
        return None


# -----------------------------------------------
# Dataset 생성 서비스
# -----------------------------------------------
def create_dataset(db: Session, uploaded_file) -> Dataset:
    """파일을 data/에 저장 → DVC add → 메타데이터를 SQLite에 저장."""

    # 1) 파일 저장 + DVC 등록
    file_path, version_info = dvc_add_file(uploaded_file)

    filename = uploaded_file.filename
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    # 2) 타입 분류
    if ext in [".csv"]:
        dtype = "csv"
    elif ext in [".txt", ".md", ".log", ".json"]:
        dtype = "text"
    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
        dtype = "image"
    elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        dtype = "video"
    else:
        dtype = "unknown"

    rows: int = 0
    cols: int = 0
    missing_rate: Dict[str, Any] = {}
    preview: Dict[str, Any] = {}

    # 3) 타입별 간단 EDA 메타
    if dtype == "csv":
        df = pd.read_csv(file_path)
        # NaN / inf 정리
        df = df.replace([float("inf"), float("-inf")], None)
        df = df.fillna(None)

        rows, cols = df.shape

        missing_dict = df.isna().mean().to_dict()
        missing_rate = clean_json_value(missing_dict)

        head_records = df.head(5).to_dict(orient="records")
        preview = clean_json_value({"head": head_records})

    elif dtype == "text":
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            rows = len(lines)
            cols = 1
            preview = {"first_lines": [ln.strip() for ln in lines[:5]]}
        except Exception:
            preview = {"first_lines": []}

    elif dtype == "image":
        try:
            img = Image.open(file_path)
            rows = img.height
            cols = img.width
            preview = {"info": f"{cols}x{rows}"}
        except Exception:
            preview = {"info": "unreadable image"}

    elif dtype == "video":
        # 가벼운 구조를 위해 외부 디펜던시(cv2 등)는 사용하지 않고,
        # 현재는 파일 크기만 메타데이터로 사용.
        rows = 0
        cols = 0
        preview = {"info": "video file", "note": "lightweight metadata only"}

    # 4) 썸네일 생성 (이미지)
    thumbnail = create_thumbnail(dtype, file_path)
    if thumbnail:
        preview["thumbnail"] = thumbnail

    # 5) Dataset 인스턴스 구성
    dataset = Dataset(
        id=str(uuid.uuid4()),
        name=filename,
        type=dtype,
        size=os.path.getsize(file_path),
        rows=rows,
        cols=cols,
        missing_rate=missing_rate,
        preview=preview,
        dvc_path=file_path,
        version="v1",  # DVC 버전 태깅은 추후 확장
    )

    # 6) DB 저장
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset
