import os
import pandas as pd
from app.services.zip_resolver import analyze_zip_dataset, analyze_roboflow
import numpy as np

def run_eda(file_path: str, dtype: str = "csv") -> dict:
    dtype = dtype.lower()

    # ------------------------
    # ZIP DATASET (폴더 기반)
    # ------------------------
    if dtype == "zip":
        # 여기서 ZIP 내부 구조와 roboflow/coco/voc/yolo 감지
        from app.services.zip_resolver import analyze_zip_dataset, analyze_roboflow

        # raw.zip이 아닌, dataset_dir/extracted 구조를 사용해야 함.
        # file_path = dvc_storage/datasets/<id>
        raw_zip = None

        # raw.zip 찾기
        for f in os.listdir(file_path):
            if f.lower().endswith(".zip"):
                raw_zip = os.path.join(file_path, f)
                break

        if not raw_zip:
            raise RuntimeError(f"ZIP dataset의 raw.zip 파일을 찾을 수 없음: {file_path}")

        info = analyze_zip_dataset(raw_zip)
        zip_type = info["zip_type"]

        result = {
            "type": "zip",
            "zip_type": zip_type,
            "stats": info["stats"],
            "tree": info["tree"],
            "images": info.get("images", []),
        }

        # ------------ roboflow 전용 EDA ------------
        if zip_type == "roboflow":
            result["roboflow"] = analyze_roboflow(info)

        return result

    # ------------------------
    # CSV EDA
    # ------------------------
    if dtype == "csv":
        df = pd.read_csv(file_path)

        # inf 값을 먼저 처리
        df = df.replace([np.inf, -np.inf], np.nan)

        # NaN → 빈 문자열로 채움 (pandas v2 호환)
        df = df.fillna("")

        # JSON-safe
        head = df.head(5).to_dict(orient="records")

        summary = df.describe(include="all").replace({np.nan: None}).to_dict()

        missing_rate = (
            df.replace("", np.nan).isna().mean().round(4).replace({np.nan: None}).to_dict()
        )

        return {
            "type": "csv",
            "shape": df.shape,
            "missing_rate": missing_rate,
            "summary": summary,
            "preview": head,
        }

    # ------------------------
    # TEXT
    # ------------------------
    if dtype == "text":
        with open(file_path, "r", errors="ignore") as f:
            lines = f.readlines()
        return {
            "type": "text",
            "num_lines": len(lines),
            "preview": lines[:20]
        }

    # ------------------------
    # FALLBACK
    # ------------------------
    return {
        "type": dtype,
        "message": "EDA not implemented for this type"
    }