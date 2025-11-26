import os
from typing import Dict, Any

import pandas as pd


def run_eda(file_path: str, dtype: str) -> Dict[str, Any]:
    """타입별로 가벼운 EDA 결과를 반환."""

    if dtype == "csv":
        df = pd.read_csv(file_path)
        summary = df.describe(include="all").fillna(0).to_dict()
        missing = df.isna().mean().to_dict()
        return {
            "shape": df.shape,
            "missing_rate": missing,
            "summary": summary,
            "type": dtype,
        }

    if dtype == "text":
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            lines = []

        lengths = [len(ln.strip()) for ln in lines]
        num_lines = len(lines)
        avg_len = sum(lengths) / num_lines if num_lines else 0

        return {
            "shape": (num_lines, 1),
            "missing_rate": {},
            "summary": {
                "num_lines": num_lines,
                "avg_line_length": avg_len,
            },
            "type": dtype,
            "preview": [ln.strip() for ln in lines[:20]],
        }

    if dtype == "image":
        try:
            from PIL import Image

            img = Image.open(file_path)
            width, height = img.size
        except Exception:
            width, height = 0, 0

        return {
            "shape": (height, width),
            "missing_rate": {},
            "summary": {
                "width": width,
                "height": height,
            },
            "type": dtype,
        }

    if dtype == "video":
        size = os.path.getsize(file_path)
        return {
            "shape": (0, 0),
            "missing_rate": {},
            "summary": {
                "size_bytes": size,
            },
            "type": dtype,
        }

    # unknown 타입
    size = os.path.getsize(file_path)
    return {
        "shape": (0, 0),
        "missing_rate": {},
        "summary": {"size_bytes": size},
        "type": dtype,
    }
