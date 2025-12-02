import os
import uuid
import shutil
import pandas as pd
from sqlalchemy.orm import Session

from app.models import Dataset, EDAResult, DriftResult
from app.services.dvc_service import (
    save_uploaded_dataset,
    process_zip_dataset,
    BASE_DATA_DIR
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

        # CSV 분석
        df = pd.read_csv(csv_path)
        rows, cols = df.shape
        preview = {"head": df.head(5).replace([float("inf"), -float("inf")], None).to_dict(orient="records")}

        dvc_path = csv_path

    # ============================================================
    # TEXT / JSON 처리
    # ============================================================
    elif dtype == "text":
        text_path = os.path.join(dataset_dir, "raw.txt")
        shutil.move(raw_original_path, text_path)

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

        preview = {
            "image_path": img_path,
            "info": "single image dataset"
        }

        dvc_path = img_path

    # ============================================================
    # 기타 포맷
    # ============================================================
    else:
        preview = {"info": f"unsupported file type: {ext}"}
        dvc_path = raw_original_path

    # ============================================================
    # Dataset DB 저장
    # ============================================================

    dataset = Dataset(
        id=dataset_id,
        name=filename,
        type=dtype,
        dvc_path=dvc_path,
        version="v1",
        preview=clean_json_value(preview),
        rows=rows,
        cols=cols,
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset


def delete_dataset(db: Session, dataset_id: str):
    """
    데이터셋과 관련된 모든 데이터를 삭제합니다.
    
    1. 관련 EDA 결과 삭제
    2. 관련 Drift 결과 삭제 (base 또는 target으로 사용된 경우)
    3. 파일 시스템에서 데이터셋 폴더 삭제
    4. Dataset DB 레코드 삭제
    """
    # 1) 데이터셋 존재 확인
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        return {"success": False, "message": "데이터셋을 찾을 수 없습니다."}

    deleted_info = {
        "dataset_id": dataset_id,
        "dataset_name": dataset.name,
        "eda_results_deleted": 0,
        "drift_results_deleted": 0,
        "files_deleted": False
    }

    # 2) 관련 EDA 결과 삭제
    eda_count = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).delete()
    deleted_info["eda_results_deleted"] = eda_count

    # 3) 관련 Drift 결과 삭제 (base_id 또는 target_id가 해당 dataset_id인 경우)
    drift_count = db.query(DriftResult).filter(
        (DriftResult.base_id == dataset_id) | (DriftResult.target_id == dataset_id)
    ).delete(synchronize_session='fetch')
    deleted_info["drift_results_deleted"] = drift_count

    # 4) 파일 시스템에서 데이터셋 폴더 삭제
    dataset_dir = os.path.join(BASE_DATA_DIR, dataset_id)
    if os.path.exists(dataset_dir):
        try:
            shutil.rmtree(dataset_dir)
            deleted_info["files_deleted"] = True
        except Exception as e:
            # 파일 삭제 실패해도 DB는 삭제 진행
            deleted_info["files_deleted"] = False
            deleted_info["file_error"] = str(e)

    # 5) Dataset 레코드 삭제
    db.delete(dataset)
    db.commit()

    return {"success": True, "deleted": deleted_info}
