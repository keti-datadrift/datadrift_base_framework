from typing import Dict, Any

import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset


def run_drift(base_path: str, target_path: str) -> Dict[str, Any]:
    """Evidently DataDriftPreset를 이용한 간단한 탭뮬러 드리프트 분석."""
    df_base = pd.read_csv(base_path)
    df_target = pd.read_csv(target_path)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=df_base, current_data=df_target)
    result = report.as_dict()

    metric = result["metrics"][0]["result"]
    overall = metric["dataset_drift"]["share_of_drifted_columns"]
    by_cols = metric["drift_by_columns"]

    features = []
    for col, data in by_cols.items():
        features.append(
            {
                "feature": col,
                "drift_score": data.get("drift_score", 0.0),
                "drift_detected": data.get("drift_detected", False),
                "stattest_name": data.get("stattest_name", ""),
            }
        )

    return {
        "overall": overall,
        "features": features,
        "raw": result,
    }
