"""R33 tests — KETI Temporal Categorical Drift detector.

Synthetic time series covering all 4 patterns (stable / sudden /
linear / cyclic) + anomaly detection + envelope shape.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from ddoc_plugin_keti_temporal.plugin import (  # noqa: E402
    DETECTOR_PREFIX,
    SUPPORTED_METHODS,
    TemporalCategoricalDriftPlugin,
    _aggregate_distribution,
    _classify_patterns,
    _compute_trend,
    _distribution_distance,
    _extract_series,
    _parse_method,
)


def _step(ts: str, dist: dict) -> dict:
    return {"timestamp": ts, "distribution": dist}


def _stable_series(n=10):
    """Same distribution N times."""
    return [_step(f"day{i}", {"red": 30, "blue": 10, "white": 5}) for i in range(n)]


def _sudden_shift_series():
    """5 stable steps, 1 huge spike, 4 more stable."""
    base = {"red": 30, "blue": 10, "white": 5}
    spike = {"red": 0, "blue": 0, "white": 45}
    return ([_step(f"d{i}", base) for i in range(5)] +
            [_step("d5", spike)] +
            [_step(f"d{i}", base) for i in range(6, 10)])


def _linear_drift_series(n=10):
    """Gradual shift from {red:30, blue:10} to {red:10, blue:30}."""
    out = []
    for i in range(n):
        # Interpolate proportionally.
        r = 30 - 2 * i
        b = 10 + 2 * i
        out.append(_step(f"d{i}", {"red": r, "blue": b}))
    return out


def _cyclic_series(n=12):
    """Daily oscillation."""
    out = []
    base = {"red": 30, "blue": 10, "white": 5}
    high = {"red": 10, "blue": 30, "white": 5}
    for i in range(n):
        out.append(_step(f"d{i}", high if i % 2 else base))
    return out


# ── dispatch / "not mine" ───────────────────────────────────────


def test_drift_detect_returns_none_for_other_detector():
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect("", "", "", "", "", "",
                               detector="jensen_shannon",
                               cfg={}, output_path="/tmp/x")
    assert out is None


def test_supported_detectors_lists_keti_keys():
    plugin = TemporalCategoricalDriftPlugin()
    decl = plugin.ddoc_supported_detectors()
    assert decl["modality"] == "categorical_series"
    assert DETECTOR_PREFIX in decl["supported"]
    assert any(":overlap" in s for s in decl["supported"])


def test_parse_method_variants():
    assert _parse_method(DETECTOR_PREFIX) == "jensen_shannon"
    assert _parse_method(f"{DETECTOR_PREFIX}:js") == "js"
    assert _parse_method(f"{DETECTOR_PREFIX}:overlap") == "overlap"


# ── pattern detection ──────────────────────────────────────────


def test_stable_series_classified_stable():
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=DETECTOR_PREFIX,
        cfg={"baseline_categorical_series": _stable_series()},
        output_path="/tmp/x",
    )
    assert out["status"] == "ok"
    assert out["overall_score"] < 0.05
    assert out["patterns"]["stable"] is True
    assert out["patterns"]["sudden_shift"] is False
    assert out["patterns"]["linear_drift"] is False


def test_sudden_shift_detected():
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=DETECTOR_PREFIX,
        cfg={"baseline_categorical_series": _sudden_shift_series()},
        output_path="/tmp/x",
    )
    assert out["status"] == "ok"
    assert out["patterns"]["sudden_shift"] is True
    # The spike at index 5 (within the 9-step current series — first was ref).
    # argmax_idx is index into current_series, which starts at original idx 1.
    assert out["trend"]["max_step"] > 0.5
    # Anomaly list non-empty.
    assert len(out["trend"]["z_anomalies"]) >= 1


def test_linear_drift_detected():
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=DETECTOR_PREFIX,
        cfg={"baseline_categorical_series": _linear_drift_series()},
        output_path="/tmp/x",
    )
    assert out["status"] == "ok"
    assert out["patterns"]["linear_drift"] is True
    assert out["trend"]["slope"] > 0.01
    # Cumulative drift accumulates as steps progress.
    assert out["trend"]["cumulative"] > 0.1


def test_cyclic_pattern_detected():
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=DETECTOR_PREFIX,
        cfg={"baseline_categorical_series": _cyclic_series()},
        output_path="/tmp/x",
    )
    assert out["status"] == "ok"
    # Cyclic detection uses lag-1 autocorrelation > threshold.
    assert out["patterns"]["cyclic"] is True


# ── envelope + I/O shape ───────────────────────────────────────


def test_envelope_carries_step_scores_with_timestamps():
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=DETECTOR_PREFIX,
        cfg={"baseline_categorical_series": _stable_series(n=4)},
        output_path="/tmp/x",
    )
    assert "step_scores" in out
    assert len(out["step_scores"]) == 3  # n=4, first becomes ref → 3 steps
    for s in out["step_scores"]:
        assert "timestamp" in s and "score" in s


def test_overlap_method_dispatch():
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=f"{DETECTOR_PREFIX}:overlap",
        cfg={"baseline_categorical_series": _sudden_shift_series()},
        output_path="/tmp/x",
    )
    assert out["status"] == "ok"
    assert out["method"] == "overlap"
    # overlap is typically more sensitive than JS — verify the spike is huge.
    assert out["trend"]["max_step"] > 0.8


# ── error paths ────────────────────────────────────────────────


def test_unknown_method_returns_error():
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=f"{DETECTOR_PREFIX}:bogus",
        cfg={}, output_path="/tmp/x",
    )
    assert out["status"] == "error"


def test_empty_baseline_returns_error():
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=DETECTOR_PREFIX,
        cfg={"baseline_categorical_series": []},
        output_path="/tmp/x",
    )
    assert out["status"] == "error"


def test_single_baseline_entry_requires_current_series():
    """1 baseline entry without current → error (need at least 2 for
    single-series mode, or ref+current split)."""
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=DETECTOR_PREFIX,
        cfg={"baseline_categorical_series": [
            _step("d0", {"red": 30, "blue": 10}),
        ]},
        output_path="/tmp/x",
    )
    assert out["status"] == "error"
    assert "at least 2" in out["message"]


def test_explicit_ref_and_current_split():
    """When current_categorical_series provided explicitly, use it
    instead of single-series mode."""
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", "", "", "", "",
        detector=DETECTOR_PREFIX,
        cfg={
            "baseline_categorical_series": [
                _step("ref0", {"red": 30, "blue": 10}),
                _step("ref1", {"red": 30, "blue": 10}),
            ],
            "current_categorical_series": [
                _step("cur0", {"red": 5, "blue": 25}),
                _step("cur1", {"red": 5, "blue": 25}),
            ],
        },
        output_path="/tmp/x",
    )
    assert out["status"] == "ok"
    assert len(out["step_scores"]) == 2
    assert out["overall_score"] > 0.1


# ── pure helpers ───────────────────────────────────────────────


def test_aggregate_distribution_normalizes_unequal_sizes():
    """First dist has 100 samples, second has 10 — they should
    contribute equally after normalization."""
    out = _aggregate_distribution([
        {"a": 70, "b": 30},
        {"a": 4, "b": 6},
    ])
    # Each input contributes 0.5 share; first is 0.7-0.3, second is 0.4-0.6.
    # Mean: a=(0.7+0.4)/2=0.55, b=(0.3+0.6)/2=0.45.
    assert abs(out["a"] - 0.55) < 1e-9
    assert abs(out["b"] - 0.45) < 1e-9


def test_distribution_distance_identical_zero():
    p = {"a": 0.7, "b": 0.3}
    q = {"a": 70, "b": 30}
    assert _distribution_distance(p, q, "jensen_shannon") < 1e-6


def test_path_mode_reads_distributions_series_json(tmp_path):
    """R38 — path mode reads `distributions_series.json` from each
    directory so ddoc analyze drift CLI can drive this plugin without
    inline cfg."""
    import json
    ref_dir = tmp_path / "ref"
    cur_dir = tmp_path / "cur"
    ref_dir.mkdir(); cur_dir.mkdir()

    ref_series = [
        _step(f"d{i}", {"red": 30, "blue": 10, "white": 5})
        for i in range(3)
    ]
    cur_series = [
        _step("d3", {"red": 30, "blue": 10, "white": 5}),
        _step("d4", {"red": 0, "blue": 0, "white": 45}),   # spike
        _step("d5", {"red": 30, "blue": 10, "white": 5}),
    ]
    (ref_dir / "distributions_series.json").write_text(json.dumps(
        {"series": ref_series}))
    (cur_dir / "distributions_series.json").write_text(json.dumps(
        {"series": cur_series}))

    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "ref", "cur", str(ref_dir), str(cur_dir), "", "",
        detector=DETECTOR_PREFIX, cfg={}, output_path="/tmp/x",
    )
    assert out["status"] == "ok"
    # 3-step current series scored.
    assert len(out["step_scores"]) == 3
    # The spike at idx 1 should be the max.
    assert out["trend"]["argmax_idx"] == 1
    assert out["trend"]["max_step"] > 0.5


def test_path_mode_missing_file_errors(tmp_path):
    plugin = TemporalCategoricalDriftPlugin()
    out = plugin.drift_detect(
        "", "", str(tmp_path / "nope-ref"), str(tmp_path / "nope-cur"),
        "", "",
        detector=DETECTOR_PREFIX, cfg={}, output_path="/tmp/x",
    )
    assert out["status"] == "error"
    assert "missing" in out["message"]


def test_distribution_distance_disjoint_one():
    p = {"a": 1.0, "b": 0.0}
    q = {"a": 0, "b": 50}
    # Disjoint distributions: JS divergence = 1.0 (max).
    score = _distribution_distance(p, q, "jensen_shannon")
    assert score > 0.99
