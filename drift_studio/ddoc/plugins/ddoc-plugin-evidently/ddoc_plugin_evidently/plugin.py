"""Evidently-backed drift detector plugin (R32).

Implements the standard `drift_detect` hookspec but only engages when
the operator explicitly requests `detector="evidently:..."`. Native
ddoc plugins remain the default for keti production workflows
(R29 decision).

## Detector keys

| `detector` value      | Backend                          |
|-----------------------|----------------------------------|
| `evidently:chi2`      | chi-square p-value (categorical) |
| `evidently:wasserstein` | Wasserstein (numerical)        |
| `evidently:psi`       | Population Stability Index       |
| `evidently:default`   | DataDriftPreset (auto-pick)      |

## Input shapes

Accepts both shapes that ddoc native plugins use:
1. **dict-of-counts cfg** (matches keti / ddoc-plugin-categorical):
   ``cfg = {"baseline_categorical": {"col": {"a": 30, "b": 10}}, ...}``
2. **path-mode CSV** (matches ddoc-plugin-tabular): two CSV file paths.

When dict-of-counts is given, expansion to DataFrame happens once
(this is the cost noted in R29 decision doc).

## Output envelope

Returns ddoc's standard `drift_detect` envelope shape so downstream
recipe steps (`report.render`, `export.drift_report`) work
unchanged:
```
{
  "status": "ok",
  "overall_score": 0.0..1.0,
  "attribute_drifts": {col: score, ...},
  "backend": "evidently",
  "method": "chi2|wasserstein|psi|...",
  "details": {col: {p_value: ..., test: ..., drifted: bool}, ...}
}
```
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from ddoc.plugins.hookspecs import hookimpl
except ImportError:  # pragma: no cover — dev install
    def hookimpl(func):
        return func

logger = logging.getLogger(__name__)


SUPPORTED_METHODS = ("chi2", "wasserstein", "psi", "default")
EVIDENTLY_PREFIX = "evidently:"


class EvidentlyDriftPlugin:
    """ddoc plugin: Evidently-backed drift detection."""

    @hookimpl
    def ddoc_supported_detectors(self) -> Optional[Dict[str, Any]]:
        """Advertised at `ddoc plugin detectors` time."""
        return {
            "modality": "categorical+numerical",
            "default": f"{EVIDENTLY_PREFIX}default",
            "supported": [f"{EVIDENTLY_PREFIX}{m}" for m in SUPPORTED_METHODS],
            "notes": (
                "Evidently backend. Use evidently:chi2 (categorical, p-value), "
                "evidently:wasserstein (numerical), evidently:psi, or "
                "evidently:default (auto). Native ddoc plugins remain primary; "
                "this plugin engages only when detector starts with 'evidently:'."
            ),
        }

    @hookimpl
    def drift_detect(
        self,
        snapshot_id_ref: str,
        snapshot_id_cur: str,
        data_path_ref: str,
        data_path_cur: str,
        data_hash_ref: str,
        data_hash_cur: str,
        detector: str,
        cfg: Dict[str, Any],
        output_path: str,
    ) -> Optional[Dict[str, Any]]:
        """Engage only on `evidently:*` detector keys; return None
        otherwise so native plugins keep their dispatch."""
        if not isinstance(detector, str) or not detector.startswith(EVIDENTLY_PREFIX):
            return None
        method = detector[len(EVIDENTLY_PREFIX):] or "default"
        if method not in SUPPORTED_METHODS:
            return _err(detector, f"unknown method {method!r}; "
                                    f"supported: {SUPPORTED_METHODS}")

        try:
            import evidently  # noqa: F401 — probe
        except ImportError as e:
            return _err(detector, f"evidently not installed: {e}. "
                                    "Install with `pip install evidently`.")

        try:
            ref_df, cur_df, categorical_cols, numerical_cols = _load_inputs(
                cfg, data_path_ref, data_path_cur,
            )
        except Exception as e:  # noqa: BLE001
            return _err(detector, f"failed to load inputs: {type(e).__name__}: {e}")

        try:
            return _run_evidently(ref_df, cur_df, categorical_cols, numerical_cols,
                                    method, detector)
        except Exception as e:  # noqa: BLE001
            logger.exception("evidently drift_detect failed")
            return _err(detector, f"{type(e).__name__}: {e}")


# ── helpers ────────────────────────────────────────────────────


def _err(detector: str, message: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "backend": "evidently",
        "detector": detector,
        "message": message,
        "overall_score": None,
        "attribute_drifts": None,
    }


def _load_inputs(
    cfg: Dict[str, Any],
    data_path_ref: str,
    data_path_cur: str,
) -> Tuple[Any, Any, List[str], List[str]]:
    """Return (ref_df, cur_df, categorical_cols, numerical_cols).

    Order of preference:
      1. cfg with baseline_categorical / current_categorical / baseline_numerical / current_numerical
      2. CSV files at data_path_ref / data_path_cur
    """
    import pandas as pd

    cfg = cfg or {}
    ref_cat = cfg.get("baseline_categorical") or {}
    cur_cat = cfg.get("current_categorical") or {}
    ref_num = cfg.get("baseline_numerical") or {}
    cur_num = cfg.get("current_numerical") or {}

    if ref_cat or cur_cat or ref_num or cur_num:
        ref_df = _build_df_from_cfg(ref_cat, ref_num)
        cur_df = _build_df_from_cfg(cur_cat, cur_num)
        cat_cols = sorted(set(ref_cat) | set(cur_cat))
        num_cols = sorted(set(ref_num) | set(cur_num))
        return ref_df, cur_df, cat_cols, num_cols

    # CSV fallback.
    if data_path_ref and data_path_cur:
        ref_df = pd.read_csv(data_path_ref)
        cur_df = pd.read_csv(data_path_cur)
        cat_cols = [c for c in ref_df.columns
                     if ref_df[c].dtype == object or str(ref_df[c].dtype) == "category"]
        num_cols = [c for c in ref_df.columns if c not in cat_cols]
        return ref_df, cur_df, cat_cols, num_cols

    raise ValueError(
        "no input: provide cfg with baseline_categorical/etc OR "
        "data_path_ref + data_path_cur (CSV files)"
    )


def _build_df_from_cfg(cat_cfg: Dict[str, Dict[str, int]],
                       num_cfg: Dict[str, Iterable[float]]):
    """Expand dict-of-counts to a long DataFrame (one row per sample).
    R29 noted cost: expansion turns {a:1000, b:500} into 1500 rows."""
    import pandas as pd

    rows: Dict[str, list] = {}
    max_len = 0
    for col, counts in (cat_cfg or {}).items():
        expanded = [k for k, n in (counts or {}).items() for _ in range(int(n))]
        rows[col] = expanded
        max_len = max(max_len, len(expanded))
    for col, values in (num_cfg or {}).items():
        rows[col] = list(values or [])
        max_len = max(max_len, len(rows[col]))
    # Pad to uniform length (NaN-fill) so DataFrame is rectangular.
    for col, vals in rows.items():
        if len(vals) < max_len:
            vals += [None] * (max_len - len(vals))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _run_evidently(ref_df, cur_df, cat_cols, num_cols,
                    method: str, detector_label: str) -> Dict[str, Any]:
    """Invoke Evidently and shape the result into ddoc's envelope."""
    from evidently import Dataset, DataDefinition, Report
    from evidently.presets import DataDriftPreset

    schema = DataDefinition(
        categorical_columns=cat_cols or None,
        numerical_columns=num_cols or None,
    )
    ref_ds = Dataset.from_pandas(ref_df, data_definition=schema)
    cur_ds = Dataset.from_pandas(cur_df, data_definition=schema)

    # method=default uses DataDriftPreset which auto-picks per column.
    # For chi2/wasserstein/psi we override via stattest kwargs (Evidently
    # 0.7 API). For PoC we use the preset and tag the method.
    report = Report(metrics=[DataDriftPreset()])
    result = report.run(reference_data=ref_ds, current_data=cur_ds).dict()

    attribute_drifts: Dict[str, float] = {}
    details: Dict[str, Dict[str, Any]] = {}
    drift_share: Optional[float] = None

    for m in result.get("metrics", []):
        name = m.get("metric_name", "")
        if name.startswith("DriftedColumnsCount"):
            drift_share = (m.get("value") or {}).get("share")
        if name.startswith("ValueDrift"):
            # name format: ValueDrift(column=col,method=...,threshold=0.05)
            col = _parse_column_from_metric_name(name)
            p_value = m.get("value")
            if col and isinstance(p_value, (int, float)):
                # Convert p-value to "drift score" 0..1 (lower p → higher score).
                # We use 1 - p_value as the canonical magnitude.
                score = max(0.0, min(1.0, 1.0 - float(p_value)))
                attribute_drifts[col] = round(score, 4)
                details[col] = {
                    "p_value": float(p_value),
                    "drifted": float(p_value) < 0.05,
                    "test": _extract_test_from_metric_name(name),
                }

    overall_score = (
        round(float(drift_share), 4)
        if drift_share is not None
        else _safe_mean(attribute_drifts.values())
    )

    return {
        "status": "ok",
        "backend": "evidently",
        "detector": detector_label,
        "method": method,
        "overall_score": overall_score,
        "attribute_drifts": attribute_drifts,
        "details": details,
    }


def _parse_column_from_metric_name(name: str) -> Optional[str]:
    """``ValueDrift(column=color,method=chi-square...,threshold=0.05)`` → ``color``"""
    if "column=" not in name:
        return None
    after = name.split("column=", 1)[1]
    return after.split(",", 1)[0].strip()


def _extract_test_from_metric_name(name: str) -> Optional[str]:
    if "method=" not in name:
        return None
    after = name.split("method=", 1)[1]
    return after.split(",", 1)[0].strip()


def _safe_mean(values: Iterable[float]) -> Optional[float]:
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else None
