"""Temporal Categorical Drift detector.

## What it does

Given a *series* of categorical distributions (each a dict-of-counts
labeled by timestamp), measure how the distribution evolves vs a
baseline. Returns per-timestamp drift scores + trend statistics that
distinguish:

| pattern        | trend                  | typical example cause              |
|----------------|------------------------|------------------------------------|
| sudden_shift   | one large drift spike   | source configuration changed      |
| linear_drift   | positive slope          | gradual sensor / source degradation |
| cyclic         | periodic ups + downs    | daily / weekly seasonality        |
| anomalous_day  | z-score > 2 on a step   | one-off external event            |
| stable         | low overall, low slope  | healthy                           |

Each pattern flag is `True/False` so downstream UIs can color-code.

## Hookspec contract

Engages on `detector` values:
- ``keti:temporal_categorical``   (default)
- ``keti:temporal_categorical:js``   (jensen-shannon per timestep, default)
- ``keti:temporal_categorical:overlap``  (1 - overlap)

Returns ddoc's standard `drift_detect` envelope shape so the result
flows through `report.render` and `export.drift_report` unchanged.

## Input shape

``cfg`` should carry:
```
{
  "baseline_categorical_series": [
    {"timestamp": "2026-05-09T00:00:00Z", "distribution": {"red": 30, "blue": 10, ...}},
    {"timestamp": "2026-05-10T00:00:00Z", "distribution": {"red": 32, "blue": 9, ...}},
    ...
  ],
  "current_categorical_series": [   # same shape — these are the steps to score
    ...
  ]
}
```

When ``current_categorical_series`` is omitted, the first entry of
``baseline_categorical_series`` is used as the reference and the rest
are scored as steps. This matches the common monitoring use case
(one source, N periodic snapshots).

## Algorithm

1. ``reference``: arithmetic mean of all baseline distributions (or
   the first one — configurable).
2. For each step in ``current_series``:
     ``step_score = jensen_shannon(reference, step.distribution)``
3. Pattern detection on the resulting score series:
     ``overall`` = mean of step scores
     ``slope``   = linear regression slope (drift / unit time, normalized)
     ``max_step`` + ``argmax_idx`` = worst step
     ``cumulative`` = sum (concept-drift accumulation proxy)
     ``z_anomalies`` = indices where z-score > 2
4. Flag patterns: sudden_shift / linear_drift / cyclic / stable.
5. Envelope assembly with all stats + per-step scores.

## Output envelope

```
{
  "status": "ok",
  "backend": "keti-temporal",
  "method": "jensen_shannon",
  "overall_score": 0.18,
  "attribute_drifts": {"color": 0.18},     # ddoc convention
  "step_scores": [{"timestamp": "...", "score": 0.04}, ...],
  "trend": {
    "slope": 0.012,
    "max_step": 0.45,
    "argmax_idx": 5,
    "cumulative": 1.23,
    "z_anomalies": [5]
  },
  "patterns": {
    "sudden_shift": true,
    "linear_drift": false,
    "cyclic": false,
    "stable": false
  }
}
```
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from ddoc.plugins.hookspecs import hookimpl
except ImportError:  # pragma: no cover
    def hookimpl(func):
        return func

logger = logging.getLogger(__name__)


DETECTOR_PREFIX = "keti:temporal_categorical"
SUPPORTED_METHODS = ("jensen_shannon", "js", "overlap")
DEFAULT_METHOD = "jensen_shannon"


# Pattern detection thresholds — tuned conservatively. Operators can
# override via cfg["thresholds"].
_DEFAULT_THRESHOLDS = {
    "stable_overall": 0.05,      # below = healthy
    "slope_significant": 0.01,   # |slope| above → linear_drift
    "sudden_z": 2.0,             # z-score above → anomalous step
    "cyclic_autocorr": 0.4,      # lag-1 autocorr above → cyclic
}


class TemporalCategoricalDriftPlugin:
    """ddoc plugin: KETI temporal categorical drift detector."""

    @hookimpl
    def ddoc_supported_detectors(self) -> Optional[Dict[str, Any]]:
        return {
            "modality": "categorical_series",
            "default": DETECTOR_PREFIX,
            "supported": [
                DETECTOR_PREFIX,
                f"{DETECTOR_PREFIX}:js",
                f"{DETECTOR_PREFIX}:overlap",
            ],
            "notes": (
                "Temporal categorical drift (KETI research). Analyzes a "
                "series of distributions over time — detects sudden_shift / "
                "linear_drift / cyclic / anomalous_day patterns from the "
                "per-timestep drift series."
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
        if not isinstance(detector, str) or not detector.startswith(DETECTOR_PREFIX):
            return None

        method = _parse_method(detector)
        if method not in SUPPORTED_METHODS:
            return _err(detector,
                         f"unknown method {method!r}; supported: {SUPPORTED_METHODS}")
        method = "jensen_shannon" if method == "js" else method

        cfg = cfg or {}
        # Path-mode (R38) — if data_path_ref/cur are provided and cfg
        # doesn't carry inline series, read `distributions_series.json`
        # from each directory. This matches ddoc CLI convention:
        # callers point `--data-path-ref` at a dir containing the
        # series file, just like ddoc-plugin-categorical reads
        # `distributions.json`.
        if data_path_ref and data_path_cur and not cfg.get("baseline_categorical_series"):
            try:
                cfg = _augment_cfg_from_paths(cfg, data_path_ref, data_path_cur)
            except Exception as e:  # noqa: BLE001
                return _err(detector, f"failed to read series files: {e}")

        try:
            ref_series, cur_series = _extract_series(cfg)
        except Exception as e:  # noqa: BLE001
            return _err(detector, f"invalid input series: {e}")

        if not cur_series:
            return _err(detector, "no current series steps to score")

        thresholds = {**_DEFAULT_THRESHOLDS, **(cfg.get("thresholds") or {})}

        # Reference distribution: arithmetic mean of baseline series (or
        # first entry when only one given).
        reference = _aggregate_distribution([s["distribution"] for s in ref_series])
        if not reference:
            return _err(detector, "reference distribution is empty")

        # Per-step scores.
        step_scores: List[Dict[str, Any]] = []
        scores_only: List[float] = []
        for step in cur_series:
            s = _distribution_distance(reference, step["distribution"], method)
            step_scores.append({
                "timestamp": step.get("timestamp"),
                "score": round(s, 4),
            })
            scores_only.append(s)

        trend = _compute_trend(scores_only, thresholds)
        patterns = _classify_patterns(scores_only, trend, thresholds)

        return {
            "status": "ok",
            "backend": "keti-temporal",
            "detector": detector,
            "method": method,
            "overall_score": round(float(np.mean(scores_only)), 4),
            "attribute_drifts": {"distribution": round(float(np.mean(scores_only)), 4)},
            "step_scores": step_scores,
            "trend": trend,
            "patterns": patterns,
        }


# ── extraction / aggregation ────────────────────────────────────


def _augment_cfg_from_paths(
    cfg: Dict[str, Any], data_path_ref: str, data_path_cur: str,
) -> Dict[str, Any]:
    """Read `<path>/distributions_series.json` from each directory
    and merge into cfg. The file shape mirrors the cfg key:
        {"series": [
            {"timestamp": "...", "distribution": {...}},
            ...
        ]}
    """
    import json
    from pathlib import Path

    new_cfg = dict(cfg)

    def _load(path: str) -> List[Dict[str, Any]]:
        p = Path(path) / "distributions_series.json"
        if not p.exists():
            raise FileNotFoundError(f"missing {p}")
        data = json.loads(p.read_text(encoding="utf-8"))
        series = data.get("series") if isinstance(data, dict) else data
        if not isinstance(series, list):
            raise ValueError(f"{p} must contain a 'series' list")
        return series

    new_cfg["baseline_categorical_series"] = _load(data_path_ref)
    new_cfg["current_categorical_series"] = _load(data_path_cur)
    return new_cfg


def _extract_series(cfg: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
    """Pull (ref_series, cur_series) from cfg in the shape documented
    above. If only ``baseline_categorical_series`` is given (no current),
    the first entry becomes the ref and the rest become the cur steps."""
    ref = cfg.get("baseline_categorical_series") or []
    cur = cfg.get("current_categorical_series") or []
    if not isinstance(ref, list) or not all(isinstance(e, dict) for e in ref):
        raise ValueError("baseline_categorical_series must be list of dicts")
    if not isinstance(cur, list) or not all(isinstance(e, dict) for e in cur):
        raise ValueError("current_categorical_series must be list of dicts")
    # Validate each entry has 'distribution'.
    for e in ref + cur:
        if "distribution" not in e or not isinstance(e["distribution"], dict):
            raise ValueError("each series entry needs a 'distribution' dict")
    # Single-series mode: first → ref, rest → cur.
    if ref and not cur:
        if len(ref) < 2:
            raise ValueError(
                "single-series mode needs at least 2 entries in "
                "baseline_categorical_series (1 ref + N steps)"
            )
        return [ref[0]], ref[1:]
    return ref, cur


def _aggregate_distribution(distributions: List[Dict[str, int]]) -> Dict[str, float]:
    """Mean of distributions, normalized so each input sums to 1 first
    (so unequal sample sizes don't bias the reference)."""
    keys: set = set()
    for d in distributions:
        keys.update(d.keys())
    out: Dict[str, float] = {k: 0.0 for k in keys}
    n = len(distributions) or 1
    for d in distributions:
        total = sum(d.values()) or 1
        for k in keys:
            out[k] += d.get(k, 0) / total
    return {k: v / n for k, v in out.items()}


# ── distance ────────────────────────────────────────────────────


def _distribution_distance(ref: Dict[str, float],
                            cur: Dict[str, int],
                            method: str) -> float:
    """Returns a value in [0, 1]. ``ref`` is already normalized; ``cur``
    is raw counts (we normalize on the fly)."""
    keys = set(ref) | set(cur)
    if not keys:
        return 0.0
    cur_total = sum(cur.values()) or 1
    p = np.array([ref.get(k, 0.0) for k in keys], dtype=np.float64)
    q = np.array([cur.get(k, 0) / cur_total for k in keys], dtype=np.float64)

    if method == "overlap":
        return float(1.0 - np.minimum(p, q).sum())
    # default: jensen_shannon (base 2 → [0, 1])
    m = 0.5 * (p + q)
    js = 0.5 * _kl(p, m) + 0.5 * _kl(q, m)
    return float(js / math.log(2))


def _kl(p: np.ndarray, q: np.ndarray) -> float:
    mask = (p > 0) & (q > 0)
    if not mask.any():
        return 0.0
    return float(np.sum(p[mask] * np.log(p[mask] / q[mask])))


# ── trend / pattern analysis ────────────────────────────────────


def _compute_trend(scores: List[float], thresholds: Dict[str, float]) -> Dict[str, Any]:
    arr = np.asarray(scores, dtype=np.float64)
    n = len(arr)
    if n == 0:
        return {"slope": 0.0, "max_step": 0.0, "argmax_idx": -1,
                "cumulative": 0.0, "z_anomalies": []}

    # Slope via simple linear regression (least squares on index, score).
    if n >= 2:
        x = np.arange(n, dtype=np.float64)
        slope = float(np.polyfit(x, arr, 1)[0])
    else:
        slope = 0.0

    # Anomalous steps: z-score > sudden_z.
    z_anomalies: List[int] = []
    if n >= 2:
        mu = float(arr.mean())
        sigma = float(arr.std())
        if sigma > 1e-9:
            z = (arr - mu) / sigma
            z_anomalies = [int(i) for i, v in enumerate(z) if v > thresholds["sudden_z"]]

    return {
        "slope": round(slope, 4),
        "max_step": round(float(arr.max()), 4),
        "argmax_idx": int(arr.argmax()),
        "cumulative": round(float(arr.sum()), 4),
        "z_anomalies": z_anomalies,
    }


def _classify_patterns(scores: List[float],
                        trend: Dict[str, Any],
                        thresholds: Dict[str, float]) -> Dict[str, bool]:
    n = len(scores)
    arr = np.asarray(scores, dtype=np.float64)
    overall = float(arr.mean()) if n else 0.0

    stable = overall < thresholds["stable_overall"] and not trend["z_anomalies"] \
        and abs(trend["slope"]) < thresholds["slope_significant"]
    linear_drift = abs(trend["slope"]) >= thresholds["slope_significant"]
    sudden_shift = bool(trend["z_anomalies"])

    # Cyclic: |lag-1 autocorrelation| above threshold. Positive r1 →
    # slow-cycle (multi-step phase), negative r1 → fast-cycle
    # (alternating). Both are "non-random temporal structure" worth
    # flagging.
    cyclic = False
    if n >= 4:
        a = arr - arr.mean()
        denom = float(np.sum(a * a))
        if denom > 1e-9:
            r1 = float(np.sum(a[:-1] * a[1:]) / denom)
            cyclic = abs(r1) > thresholds["cyclic_autocorr"]

    return {
        "sudden_shift": bool(sudden_shift),
        "linear_drift": bool(linear_drift),
        "cyclic": bool(cyclic),
        "stable": bool(stable),
    }


# ── error envelope ─────────────────────────────────────────────


def _err(detector: str, message: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "backend": "keti-temporal",
        "detector": detector,
        "message": message,
        "overall_score": None,
        "attribute_drifts": None,
    }


def _parse_method(detector: str) -> str:
    """``"keti:temporal_categorical"`` → ``"jensen_shannon"`` (default)
    ``"keti:temporal_categorical:overlap"`` → ``"overlap"``"""
    if detector == DETECTOR_PREFIX:
        return DEFAULT_METHOD
    parts = detector[len(DETECTOR_PREFIX):].lstrip(":").strip()
    return parts or DEFAULT_METHOD
