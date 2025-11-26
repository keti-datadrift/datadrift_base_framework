import pandas as pd

def run_eda(file_path: str) -> dict:
    df = pd.read_csv(file_path)

    summary = df.describe(include="all").fillna(0).to_dict()
    missing = df.isna().mean().to_dict()

    return {
        "shape": df.shape,
        "missing_rate": missing,
        "summary": summary,
    }