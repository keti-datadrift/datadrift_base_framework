import os
import json
import pandas as pd
import numpy as np

from app.services.zip_resolver import analyze_zip_dataset, analyze_roboflow
from app.utils.json_sanitize import clean_json_value


# ============================================================
# ZIP vs ZIP DRIFT
# ============================================================

def compute_zip_drift(base_info, target_info):
    """
    ZIP dataset drift:
        - split distribution 변화
        - class distribution 변화
        - annotation 수 변화
        - 디렉토리 구조 변화
        - 이미지 수 변화
    """

    zip_type = base_info.get("zip_type")

    drift = {
        "zip_type": zip_type,
        "structure": {},
        "splits": {},
        "classes": {},
        "summary": {},
    }

    # ----------------------------------------------------------
    # 1. 구조 비교
    # ----------------------------------------------------------
    drift["structure"] = {
        "base_subdirs": base_info["stats"].get("subdirs", []),
        "target_subdirs": target_info["stats"].get("subdirs", []),
    }

    # ----------------------------------------------------------
    # 2. Roboflow ZIP Drift
    # ----------------------------------------------------------
    if zip_type == "roboflow":
        b = analyze_roboflow(base_info)
        t = analyze_roboflow(target_info)

        # split drift
        split_names = ["train", "valid", "test"]
        for s in split_names:
            drift["splits"][s] = {
                "base": b["splits"][s]["num_images"],
                "target": t["splits"][s]["num_images"],
                "delta": t["splits"][s]["num_images"] - b["splits"][s]["num_images"],
            }

        # class drift
        all_classes = set(b["classes"]) | set(t["classes"])
        for c in all_classes:
            base_cnt = sum([b["splits"][s]["class_counts"].get(c, 0) for s in split_names])
            target_cnt = sum([t["splits"][s]["class_counts"].get(c, 0) for s in split_names])

            drift["classes"][c] = {
                "base": base_cnt,
                "target": target_cnt,
                "delta": target_cnt - base_cnt,
            }

        drift["summary"] = {
            "total_images_base": sum([b["splits"][s]["num_images"] for s in split_names]),
            "total_images_target": sum([t["splits"][s]["num_images"] for s in split_names]),
        }

        return drift

    # ----------------------------------------------------------
    # 3. 일반 YOLO / COCO / VOC Drift (단순 통계)
    # ----------------------------------------------------------
    # 이미지 개수 변화
    drift["summary"]["base_images"] = base_info["stats"]["image_files"]
    drift["summary"]["target_images"] = target_info["stats"]["image_files"]
    drift["summary"]["delta_images"] = (
        target_info["stats"]["image_files"] - base_info["stats"]["image_files"]
    )

    # 텍스트/annotation 변화
    drift["summary"]["base_text"] = base_info["stats"]["text_files"]
    drift["summary"]["target_text"] = target_info["stats"]["text_files"]
    drift["summary"]["delta_text"] = (
        target_info["stats"]["text_files"] - base_info["stats"]["text_files"]
    )

    return drift


# ============================================================
# CSV vs CSV DRIFT
# ============================================================

def compute_csv_drift(base_path, target_path):
    print('base_path = ', base_path)
    print('target_path = ', target_path)
    df1 = pd.read_csv(base_path)
    df2 = pd.read_csv(target_path)
    print(df1)
    print(df2)

    # 수치형 컬럼만 비교
    numeric_cols = [c for c in df1.columns if pd.api.types.is_numeric_dtype(df1[c])]

    drift = {}

    for col in numeric_cols:
        mean1 = df1[col].mean()
        mean2 = df2[col].mean()
        drift[col] = {
            "base_mean": None if pd.isna(mean1) else round(float(mean1), 4),
            "target_mean": None if pd.isna(mean2) else round(float(mean2), 4),
            "delta": None if pd.isna(mean1) or pd.isna(mean2) else round(float(mean2 - mean1), 4),
        }
    print('drift = ', drift)

    return drift


# ============================================================
# ZIP vs CSV / TEXT vs CSV / unsupported
# ============================================================

def run_drift(base_path, target_path):
    """
    base_path, target_path:
        ZIP → dataset_dir (폴더)
        CSV/TXT/IMAGE → 단일 파일
    """

    # -------------------
    # ZIP vs ZIP
    # -------------------
    if os.path.isdir(base_path) and os.path.isdir(target_path):
        # raw.zip 찾기
        def locate_raw_zip(path):
            for f in os.listdir(path):
                if f.lower().endswith(".zip"):
                    return os.path.join(path, f)
            return None

        base_zip = locate_raw_zip(base_path)
        target_zip = locate_raw_zip(target_path)

        if not base_zip or not target_zip:
            raise RuntimeError("ZIP dataset drift: raw.zip 파일을 찾을 수 없습니다.")

        base_info = analyze_zip_dataset(base_zip)
        target_info = analyze_zip_dataset(target_zip)

        result = compute_zip_drift(base_info, target_info)
        result["type"] = "zip_zip"
        return clean_json_value(result)

    # -------------------
    # CSV vs CSV
    # -------------------
    if base_path.endswith(".csv") and target_path.endswith(".csv"):
        result = compute_csv_drift(base_path, target_path)
        return clean_json_value({"type": "csv_csv", "drift": result})

    # -------------------
    # 다른 조합은 미지원 (향후 추가 가능)
    # -------------------
    return clean_json_value({
        "type": "unsupported",
        "message": f"Drift not supported between {base_path} and {target_path}"
    })