"""R32 — tests for ddoc-plugin-evidently."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Plugin import path.
_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from ddoc_plugin_evidently.plugin import (  # noqa: E402
    EVIDENTLY_PREFIX,
    SUPPORTED_METHODS,
    EvidentlyDriftPlugin,
    _build_df_from_cfg,
    _parse_column_from_metric_name,
    _extract_test_from_metric_name,
    _safe_mean,
)


# ── dispatch / "not mine" semantics ──────────────────────────────


def test_drift_detect_returns_none_for_non_evidently_detector():
    """Native ddoc detectors must keep their dispatch."""
    plugin = EvidentlyDriftPlugin()
    result = plugin.drift_detect(
        "ref", "cur", "", "", "", "",
        detector="jensen_shannon",
        cfg={}, output_path="/tmp/x",
    )
    assert result is None


def test_drift_detect_returns_error_for_unknown_method():
    plugin = EvidentlyDriftPlugin()
    result = plugin.drift_detect(
        "ref", "cur", "", "", "", "",
        detector="evidently:bogus",
        cfg={}, output_path="/tmp/x",
    )
    assert result["status"] == "error"
    assert "unknown method" in result["message"]


def test_supported_detectors_lists_evidently_methods():
    plugin = EvidentlyDriftPlugin()
    decl = plugin.ddoc_supported_detectors()
    assert decl["modality"] == "categorical+numerical"
    supported = decl["supported"]
    assert "evidently:chi2" in supported
    assert "evidently:wasserstein" in supported
    assert decl["default"].startswith(EVIDENTLY_PREFIX)


# ── happy path with real Evidently (skip if missing) ────────────


evidently_avail = pytest.importorskip("evidently",
                                       reason="evidently not installed; PoC test")


def test_drift_detect_categorical_real_evidently():
    plugin = EvidentlyDriftPlugin()
    cfg = {
        "baseline_categorical": {"color": {"red": 30, "blue": 10, "white": 5}},
        "current_categorical":  {"color": {"red": 5,  "blue": 25, "white": 20}},
    }
    result = plugin.drift_detect(
        "ref", "cur", "", "", "", "",
        detector="evidently:default",
        cfg=cfg, output_path="/tmp/x",
    )
    assert result["status"] == "ok"
    assert result["backend"] == "evidently"
    assert result["method"] == "default"
    assert "color" in (result.get("attribute_drifts") or {})
    # Big shift → score close to 1.0 (low p-value → high drift score).
    assert result["attribute_drifts"]["color"] > 0.9


def test_drift_detect_identical_distributions_low_score():
    plugin = EvidentlyDriftPlugin()
    same = {"color": {"red": 30, "blue": 10, "white": 5}}
    cfg = {"baseline_categorical": same, "current_categorical": same}
    result = plugin.drift_detect(
        "ref", "cur", "", "", "", "",
        detector="evidently:chi2",
        cfg=cfg, output_path="/tmp/x",
    )
    assert result["status"] == "ok"
    # p-value=1.0 → drift score 0.
    score = result["attribute_drifts"].get("color")
    assert score is not None and score < 0.1


# ── helpers ─────────────────────────────────────────────────────


def test_build_df_from_cfg_expands_counts():
    df = _build_df_from_cfg({"c": {"a": 3, "b": 2}}, {})
    assert len(df) == 5
    assert set(df["c"]) == {"a", "b"}


def test_build_df_from_cfg_pads_uneven_columns():
    df = _build_df_from_cfg(
        {"c": {"a": 2, "b": 1}},
        {"n": [0.1, 0.2, 0.3, 0.4]},
    )
    assert len(df) == 4
    # categorical col padded with None.
    assert df["c"].isna().sum() == 1


def test_parse_column_from_metric_name():
    name = "ValueDrift(column=color,method=chi-square p_value,threshold=0.05)"
    assert _parse_column_from_metric_name(name) == "color"
    assert _parse_column_from_metric_name("DriftedColumnsCount(drift_share=0.5)") is None


def test_extract_test_from_metric_name():
    name = "ValueDrift(column=color,method=chi-square,threshold=0.05)"
    assert _extract_test_from_metric_name(name) == "chi-square"


def test_safe_mean():
    assert _safe_mean([0.2, 0.4, 0.6]) == 0.4
    assert _safe_mean([]) is None
    assert _safe_mean([None, "bogus"]) is None
