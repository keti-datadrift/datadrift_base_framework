import pandas as pd

def simple_drift(df_base: pd.DataFrame, df_target: pd.DataFrame):
    """
    매우 단순한 드리프트 계산 (컬럼별 평균 차이 비교)
    향후 PSI, KS 등으로 변경 가능
    """
    results = []
    numeric_cols = df_base.select_dtypes("number").columns

    for col in numeric_cols:
        b = df_base[col].mean()
        t = df_target[col].mean()
        diff = abs(b - t)

        results.append({
            "feature": col,
            "mean_base": float(b),
            "mean_target": float(t),
            "drift_score": float(diff)
        })

    overall = sum([r["drift_score"] for r in results]) / len(results)

    return {
        "overall_drift": overall,
        "features": results
    }