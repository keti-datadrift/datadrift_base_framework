import pandas as pd

def simple_eda(df: pd.DataFrame):
    """
    가장 단순한 EDA - 추후 확장 쉬움(Evidently 등)
    """
    summary = df.describe(include="all").fillna(0).to_dict()
    missing = df.isna().mean().to_dict()

    return {
        "shape": df.shape,
        "missing_rate": missing,
        "summary": summary,
    }