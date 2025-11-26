import pandas as pd
#from evidently.report import Report
#from evidently.metric_preset import DataDriftPreset

def run_drift(base_path: str, target_path: str) -> dict:
    df_base = pd.read_csv(base_path)
    df_target = pd.read_csv(target_path)

    '''
    # Evidently DataDriftPreset 사용
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=df_base, current_data=df_target)

    result = report.as_dict()

    # 간단한 요약 추출
    overall = result["metrics"][0]["result"]["dataset_drift"]["share_of_drifted_columns"]
    feature_results = result["metrics"][0]["result"]["drift_by_columns"]

    feature_drift = []
    for col, data in feature_results.items():
        feature_drift.append({
            "feature": col,
            "drift_score": data.get("drift_score", 0),
            "drift_detected": data.get("drift_detected", False),
            "stattest_name": data.get("stattest_name", ""),
        })
    '''
    overall = 'todo'
    feature_drift = 'todo'
    result = 'todo'
    
    return {
        "overall": overall,
        "features": feature_drift,
        "raw": result,  # 디버깅용
    }