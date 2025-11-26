import os
import uuid
import shutil
import pandas as pd
from sqlalchemy.orm import Session

from app.models import Dataset
from app.services.dvc_service import (
    dvc_add_file,
    save_uploaded_dataset,
    process_zip_dataset
)
from app.utils.json_sanitize import clean_json_value


def create_dataset(db: Session, uploaded_file):
    # 1) 공통 저장 로직 (dataset 폴더만 생성)
    dataset_id, raw_original_path = save_uploaded_dataset(uploaded_file)

    filename = uploaded_file.filename
    ext = os.path.splitext(filename)[1].lower()

    dtype = {
        ".zip": "zip",
        ".csv": "csv",
        ".txt": "text",
        ".json": "text",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
    }.get(ext, "unknown")

    preview = {}
    rows, cols = 0, 0

    dataset_dir = os.path.dirname(raw_original_path)

    # ============================================================
    # ZIP 처리
    # ============================================================
    if dtype == "zip":
        info = process_zip_dataset(dataset_id, raw_original_path)

        preview = {
            "zip_type": info["zip_type"],
            "tree": info["tree"],
            "stats": info["stats"],
            "images": info.get("images", [])
        }

        dvc_path = dataset_dir  # ZIP은 전체 폴더를 관리

    # ============================================================
    # CSV 처리 (단일 파일)
    # ============================================================
    elif dtype == "csv":
        # raw.csv 로 고정 저장
        csv_path = os.path.join(dataset_dir, "raw.csv")
        shutil.move(raw_original_path, csv_path)

        # DVC ADD (단일 파일만 추적)
        dvc_add_file(csv_path)

        # CSV 분석
        df = pd.read_csv(csv_path)
        rows, cols = df.shape
        preview = {"head": df.head(5).replace([float("inf"), -float("inf")], None).to_dict(orient="records")}

        dvc_path = csv_path  # CSV는 파일 경로만 dvc_path로 저장

    # ============================================================
    # TEXT / JSON 처리
    # ============================================================
    elif dtype == "text":
        text_path = os.path.join(dataset_dir, "raw.txt")
        shutil.move(raw_original_path, text_path)

        # DVC ADD
        dvc_add_file(text_path)

        with open(text_path, "r", errors="ignore") as f:
            lines = f.readlines()

        preview = {"first_lines": lines[:20]}

        dvc_path = text_path

    # ============================================================
    # IMAGE 처리 (png/jpg/jpeg)
    # ============================================================
    elif dtype == "image":
        img_path = os.path.join(dataset_dir, filename)
        shutil.move(raw_original_path, img_path)

        dvc_add_file(img_path)

        preview = {
            "image_path": img_path,
            "info": "single image dataset"
        }

        dvc_path = img_path

    # ============================================================
    # 기타 포맷
    # ============================================================
    else:
        # 그래도 파일은 그대로 저장해둔다
        dvc_add_file(raw_original_path)
        preview = {"info": f"unsupported file type: {ext}"}
        dvc_path = raw_original_path

    # ============================================================
    # Dataset DB 저장
    # ============================================================

    dataset = Dataset(
        id=dataset_id,
        name=filename,
        type=dtype,
        dvc_path=dvc_path,    # ← 여기! 타입별로 저장된 dvc_path 사용
        version="v1",
        preview=clean_json_value(preview),
        rows=rows,
        cols=cols,
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset

