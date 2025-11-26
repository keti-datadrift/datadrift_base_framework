import pandas as pd
from app.services.zip_resolver import analyze_zip_dataset, analyze_roboflow


def run_eda(file_path: str, dtype: str = "csv") -> dict:
    # ---- ZIP: Roboflow/YOLO/COCO/VOC 등 구조 분석 ----
    if dtype == "zip":
        info = analyze_zip_dataset(file_path)

        result = {
            "type": "zip",
            "zip_type": info["zip_type"],
            "stats": info["stats"],
            "tree": info["tree"],
        }

        if info["zip_type"] == "roboflow":
            result["roboflow"] = analyze_roboflow(info)

        return result

    # ---- CSV ----
    if dtype == "csv":
        df = pd.read_csv(file_path)
        summary = df.describe(include="all").fillna(0).to_dict()
        missing = df.isna().mean().to_dict()

        return {
            "type": "csv",
            "shape": df.shape,
            "missing_rate": missing,
            "summary": summary,
        }

    # ---- TEXT ----
    if dtype == "text":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        lengths = [len(line.strip()) for line in lines]
        return {
            "type": "text",
            "num_lines": len(lines),
            "avg_line_length": (sum(lengths) / len(lengths)) if lengths else 0,
            "preview": [ln.strip() for ln in lines[:20]],
        }

    # ---- Fallback ----
    return {
        "type": dtype,
        "info": "EDA not implemented for this type yet.",
    }