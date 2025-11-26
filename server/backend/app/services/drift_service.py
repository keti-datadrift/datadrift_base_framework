import pandas as pd
import numpy as np

def _compute_psi(expected, actual, bins=10):
    """
    Population Stability Index(PSI)를 아주 단순하게 구현한 함수
    expected, actual: 1차원 numpy array
    """
    # NaN 제거
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # 공통 구간(bin) 생성
    bins_edges = np.linspace(
        min(expected.min(), actual.min()),
        max(expected.max(), actual.max()),
        bins + 1,
    )

    expected_counts, _ = np.histogram(expected, bins=bins_edges)
    actual_counts, _ = np.histogram(actual, bins=bins_edges)

    # 비율로 변경 + 0 방지용 epsilon
    expected_perc = expected_counts / (len(expected) + 1e-8)
    actual_perc = actual_counts / (len(actual) + 1e-8)

    epsilon = 1e-8
    psi = np.sum(
        (expected_perc - actual_perc)
        * np.log((expected_perc + epsilon) / (actual_perc + epsilon))
    )

    if np.isnan(psi) or np.isinf(psi):
        return 0.0

    return float(psi)


def run_drift(base_path: str, target_path: str) -> dict:
    """
    간단한 수치형 컬럼 PSI 기반 드리프트 분석
    - overall: 전체 수치형 컬럼 PSI 평균
    - features: 컬럼별 PSI 상세
    """
    df_base = pd.read_csv(base_path)
    df_target = pd.read_csv(target_path)

    # 공통 컬럼만 비교
    common_cols = [c for c in df_base.columns if c in df_target.columns]

    numeric_cols = []
    for c in common_cols:
        if pd.api.types.is_numeric_dtype(df_base[c]):
            numeric_cols.append(c)

    feature_results = []
    psi_values = []

    for col in numeric_cols:
        base_vals = df_base[col].astype(float).to_numpy()
        target_vals = df_target[col].astype(float).to_numpy()

        psi = _compute_psi(base_vals, target_vals)
        psi_values.append(psi)

        feature_results.append(
            {
                "feature": col,
                "psi": psi,
                "drift_flag": psi > 0.2,  # 임계값은 예시
            }
        )

    overall = float(np.mean(psi_values)) if psi_values else 0.0

    return {
        "overall": overall,
        "features": feature_results,
    }

def run_zip_drift(base_info, target_info):
    drift = {
        "class_distribution": {},
        "split_distribution": {},
        "structure_changes": {},
    }

    # 1. split 변화
    for split in ["train", "valid", "test"]:
        b = base_info["splits"].get(split, {})
        t = target_info["splits"].get(split, {})
        drift["split_distribution"][split] = {
            "base_images": b.get("num_images", 0),
            "target_images": t.get("num_images", 0),
            "delta": (t.get("num_images", 0) - b.get("num_images", 0)),
        }

    # 2. class distribution 변화
    for cls in base_info["classes"]:
        b = sum([s["class_counts"].get(cls, 0) for s in base_info["splits"].values()])
        t = sum([s["class_counts"].get(cls, 0) for s in target_info["splits"].values()])
        drift["class_distribution"][cls] = {
            "base": b,
            "target": t,
            "delta": t - b
        }

    # 3. 구조 변경
    drift["structure_changes"] = {
        "base_dirs": base_info["stats"]["subdirs"],
        "target_dirs": target_info["stats"]["subdirs"]
    }

    return drift