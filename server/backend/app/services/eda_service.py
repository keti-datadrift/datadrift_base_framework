import os
import json
import pandas as pd
import numpy as np

from app.utils.json_sanitize import clean_json_value
from app.services.zip_resolver import (
    analyze_zip_dataset,
    analyze_roboflow,
    analyze_yolo,
    analyze_voc,
    analyze_coco,
)


def run_eda(file_path: str, dtype: str = "csv") -> dict:
    """
    file_path:
        CSV → raw.csv
        ZIP → dvc_storage/datasets/<id>/   (폴더)
        TEXT → raw.txt
        IMAGE → raw.png

    dtype: csv | zip | text | image | unknown
    """
    dtype = dtype.lower()

    # =========================================================
    # ZIP DATASET EDA
    # =========================================================
    if dtype == "zip":
        # file_path = dvc_storage/datasets/<id>/
        dataset_dir = file_path

        # raw.zip 찾기
        raw_zip = None
        for f in os.listdir(dataset_dir):
            if f.lower().endswith(".zip"):
                raw_zip = os.path.join(dataset_dir, f)
                break

        if not raw_zip:
            raise RuntimeError(f"ZIP Dataset EDA: raw.zip 파일을 찾을 수 없음: {dataset_dir}")

        # ZIP 분석 (roboflow/yolo/voc/coco 자동 감지)
        info = analyze_zip_dataset(raw_zip)

        zip_type = info.get("zip_type", "unknown")

        result = {
            "type": "zip",
            "zip_type": zip_type,
            "tree": info.get("tree"),
            "stats": info.get("stats"),
            "images": info.get("images", []),
        }

        # -----------------------
        # Roboflow EDA
        # -----------------------
        if zip_type == "roboflow":
            result["roboflow"] = analyze_roboflow(info)

        # -----------------------
        # YOLO EDA
        # -----------------------
        elif zip_type == "yolo":
            result["yolo"] = analyze_yolo(info)

        # -----------------------
        # VOC EDA
        # -----------------------
        elif zip_type == "voc":
            result["voc"] = analyze_voc(info)

        # -----------------------
        # COCO EDA
        # -----------------------
        elif zip_type == "coco":
            result["coco"] = analyze_coco(info)

        return clean_json_value(result)

    # =========================================================
    # CSV EDA
    # =========================================================
    if dtype == "csv":
        df = pd.read_csv(file_path)

        # inf → NaN
        df = df.replace([np.inf, -np.inf], np.nan)

        # NaN → "" (Pandas v2에서 None 불가)
        df = df.fillna("")

        # Preview (5 rows)
        preview = df.head(5).to_dict(orient="records")

        # Summary
        summary = df.describe(include="all").replace({np.nan: None}).to_dict()

        # Missing rate
        missing_rate = (
            df.replace("", np.nan).isna().mean().round(4).replace({np.nan: None}).to_dict()
        )

        return clean_json_value({
            "type": "csv",
            "shape": df.shape,
            "missing_rate": missing_rate,
            "summary": summary,
            "preview": preview,
        })

    # =========================================================
    # TEXT / JSON EDA
    # =========================================================
    if dtype == "text":
        with open(file_path, "r", errors="ignore") as f:
            lines = f.readlines()

        # JSON 파일일 수도 있으니 우선 파싱 시도
        json_data = None
        try:
            with open(file_path, "r", errors="ignore") as j:
                json_data = json.load(j)
        except Exception:
            pass  # TEXT로 처리

        result = {
            "type": "text",
            "num_lines": len(lines),
            "first_lines": lines[:20],
        }

        if json_data:
            result["json"] = json_data

        return clean_json_value(result)

    # =========================================================
    # IMAGE EDA
    # =========================================================
    if dtype == "image":
        # 단일 이미지이므로 간단하게 metadata만 반환
        return {
            "type": "image",
            "image_path": file_path,
            "info": "Single image dataset (no annotations)",
        }

    # =========================================================
    # UNKNOWN TYPE
    # =========================================================
    return clean_json_value({
        "type": dtype,
        "info": f"EDA not implemented for type {dtype}",
    })