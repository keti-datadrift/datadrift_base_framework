"""Round-26 (Track A) — categorical-distribution drift plugin tests.

Closes the shape gap discovered in Round 25 — keti's vehicle
fingerprint drift (color / type / hourly distributions) was not
expressible through any existing ddoc modality. This plugin provides
the jensen_shannon + overlap detectors over dict-of-counts.

Tests cover:
* pure-function math correctness (reference values from
  hand-calculated and matched against keti's existing implementation)
* plugin file-mode (read distributions.json from data path)
* plugin inline-cfg mode (cfg.baseline_categorical / .current_categorical)
* unsupported-detector envelope shape
* End-to-end via /analyze/drift
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

from ddoc_plugin_categorical.categorical_impl import (
    CategoricalDriftPlugin,
    jensen_shannon,
    overlap_distance,
)


# ── pure-function math ──────────────────────────────────────────────


def test_jensen_shannon_identical_dists_zero():
    assert jensen_shannon({"a": 5, "b": 5}, {"a": 5, "b": 5}) == 0.0


def test_jensen_shannon_disjoint_dists_one():
    # Completely non-overlapping sets → JSD = 1 (max).
    assert jensen_shannon({"a": 10}, {"b": 10}) == 1.0


def test_jensen_shannon_symmetric():
    a = {"red": 30, "blue": 10, "white": 5}
    b = {"red": 5, "blue": 25, "white": 20}
    s1 = jensen_shannon(a, b)
    s2 = jensen_shannon(b, a)
    assert abs(s1 - s2) < 1e-12


def test_jensen_shannon_in_unit_interval():
    a = {"x": 1, "y": 2, "z": 3}
    b = {"x": 3, "y": 2, "z": 1}
    s = jensen_shannon(a, b)
    assert 0.0 <= s <= 1.0


def test_jensen_shannon_matches_keti_reference():
    """Match the same math used in
    ``keti_veritas/app/services/dia/comparison.py:jensen_shannon_divergence``.
    Reference value computed by directly running keti's implementation
    on the same inputs (cross-checked 2026-05-10) — *byte-equivalent*
    so a caller switching from local computation to ``ddoc analyze
    drift --modality=categorical`` gets identical scores."""
    a = {"sedan": 60, "suv": 30, "truck": 10}
    b = {"sedan": 50, "suv": 30, "truck": 20}
    expected = 0.015539008579500468
    got = jensen_shannon(a, b)
    assert abs(got - expected) < 1e-15


def test_overlap_distance_identical_zero():
    assert overlap_distance({"a": 5}, {"a": 5}) == 0.0


def test_overlap_distance_disjoint_one():
    assert overlap_distance({"a": 5}, {"b": 5}) == 1.0


def test_overlap_distance_symmetric():
    a = {"red": 10, "blue": 5}
    b = {"red": 5, "blue": 10}
    assert overlap_distance(a, b) == overlap_distance(b, a)


# ── plugin: file mode ───────────────────────────────────────────────


def _write_distributions(path: Path, data: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "distributions.json").write_text(json.dumps(data), encoding="utf-8")


def _identical_pair(tmp_path: Path) -> tuple[Path, Path]:
    ref = tmp_path / "ref"
    cur = tmp_path / "cur"
    payload = {
        "color_distribution": {"red": 10, "blue": 5, "white": 12},
        "type_distribution": {"sedan": 8, "suv": 7, "truck": 4},
    }
    _write_distributions(ref, payload)
    _write_distributions(cur, payload)
    return ref, cur


def _shifted_pair(tmp_path: Path) -> tuple[Path, Path]:
    ref = tmp_path / "ref"
    cur = tmp_path / "cur"
    _write_distributions(ref, {
        "color_distribution": {"red": 30, "blue": 10, "white": 5},
        "type_distribution": {"sedan": 60, "suv": 30, "truck": 10},
    })
    _write_distributions(cur, {
        "color_distribution": {"red": 5, "blue": 25, "white": 20},
        "type_distribution": {"sedan": 50, "suv": 30, "truck": 20},
    })
    return ref, cur


def test_plugin_drift_zero_for_identical_distributions(tmp_path: Path):
    plugin = CategoricalDriftPlugin()
    ref, cur = _identical_pair(tmp_path)
    out = tmp_path / "out"
    env = plugin.drift_detect(
        snapshot_id_ref="x", snapshot_id_cur="y",
        data_path_ref=str(ref), data_path_cur=str(cur),
        data_hash_ref="", data_hash_cur="",
        detector="default", cfg={}, output_path=str(out),
    )
    assert env is not None
    assert env["status"] == "success"
    assert env["modality"] == "categorical"
    assert env["detector"] == "default"
    assert env["overall_score"] == 0.0
    assert all(v == 0.0 for v in env["attribute_drifts"].values())
    # metrics.json was written
    assert (out / "metrics.json").exists()


def test_plugin_drift_nonzero_for_shifted(tmp_path: Path):
    plugin = CategoricalDriftPlugin()
    ref, cur = _shifted_pair(tmp_path)
    out = tmp_path / "out"
    env = plugin.drift_detect(
        snapshot_id_ref="x", snapshot_id_cur="y",
        data_path_ref=str(ref), data_path_cur=str(cur),
        data_hash_ref="", data_hash_cur="",
        detector="default", cfg={}, output_path=str(out),
    )
    assert env["overall_score"] > 0.0
    assert env["attribute_drifts"]["color_distribution"] > 0.0
    assert env["attribute_drifts"]["type_distribution"] > 0.0


def test_plugin_returns_none_when_no_distributions(tmp_path: Path):
    """If no distributions.json present, plugin must defer (return None)
    so other modality plugins get a chance."""
    plugin = CategoricalDriftPlugin()
    ref = tmp_path / "ref"
    cur = tmp_path / "cur"
    ref.mkdir()
    cur.mkdir()
    out = tmp_path / "out"
    env = plugin.drift_detect(
        snapshot_id_ref="", snapshot_id_cur="",
        data_path_ref=str(ref), data_path_cur=str(cur),
        data_hash_ref="", data_hash_cur="",
        detector="default", cfg={}, output_path=str(out),
    )
    assert env is None


def test_plugin_inline_cfg_overrides_file(tmp_path: Path):
    """Round 25 friction precedent: inline cfg lets callers skip the
    disk round-trip entirely. baseline_categorical / current_categorical
    in cfg take precedence over distributions.json."""
    plugin = CategoricalDriftPlugin()
    ref, cur = _identical_pair(tmp_path)  # files exist but inline overrides
    out = tmp_path / "out"
    env = plugin.drift_detect(
        snapshot_id_ref="x", snapshot_id_cur="y",
        data_path_ref=str(ref), data_path_cur=str(cur),
        data_hash_ref="", data_hash_cur="",
        detector="js",
        cfg={
            "baseline_categorical": {"color": {"red": 10}},
            "current_categorical": {"color": {"blue": 10}},
        },
        output_path=str(out),
    )
    assert env["overall_score"] == 1.0  # disjoint → max JSD


def test_plugin_unsupported_detector_envelope(tmp_path: Path):
    plugin = CategoricalDriftPlugin()
    ref, cur = _identical_pair(tmp_path)
    out = tmp_path / "out"
    env = plugin.drift_detect(
        snapshot_id_ref="", snapshot_id_cur="",
        data_path_ref=str(ref), data_path_cur=str(cur),
        data_hash_ref="", data_hash_cur="",
        detector="mmd", cfg={}, output_path=str(out),
    )
    assert env["status"] == "error"
    assert env["error_code"] == "unsupported_detector"
    assert "mmd" in env["message"]


def test_plugin_overlap_strategy(tmp_path: Path):
    plugin = CategoricalDriftPlugin()
    ref, cur = _shifted_pair(tmp_path)
    out = tmp_path / "out"
    env = plugin.drift_detect(
        snapshot_id_ref="", snapshot_id_cur="",
        data_path_ref=str(ref), data_path_cur=str(cur),
        data_hash_ref="", data_hash_cur="",
        detector="overlap", cfg={}, output_path=str(out),
    )
    assert env["detector"] == "overlap"
    assert 0.0 < env["overall_score"] <= 1.0


def test_plugin_attribute_weights(tmp_path: Path):
    """Cfg-supplied per-attribute weights override the equal-weight default."""
    plugin = CategoricalDriftPlugin()
    ref, cur = _shifted_pair(tmp_path)
    out = tmp_path / "out"
    env = plugin.drift_detect(
        snapshot_id_ref="", snapshot_id_cur="",
        data_path_ref=str(ref), data_path_cur=str(cur),
        data_hash_ref="", data_hash_cur="",
        detector="default",
        cfg={"attribute_weights": {"color_distribution": 1.0,
                                    "type_distribution": 0.0}},
        output_path=str(out),
    )
    # With weight 0 on type, overall should equal the color score exactly.
    assert env["overall_score"] == env["attribute_drifts"]["color_distribution"]


# ── plugin discovery + supported_detectors ──────────────────────────


def test_plugin_supported_detectors_metadata():
    plugin = CategoricalDriftPlugin()
    meta = plugin.ddoc_supported_detectors()
    assert meta["modality"] == "categorical"
    assert "jensen_shannon" in meta["supported"]
    assert "overlap" in meta["supported"]
    assert meta["default"] == "jensen_shannon"


def test_plugin_get_metadata():
    plugin = CategoricalDriftPlugin()
    meta = plugin.ddoc_get_metadata()
    assert meta["name"] == "ddoc-plugin-categorical"
    assert meta["modality"] == "categorical"


def test_entry_point_registered():
    """The plugin must be discoverable via the ``ddoc`` entry-point
    group so ``ddoc plugin list`` and the host CLI find it."""
    from importlib.metadata import entry_points
    found = [ep.name for ep in entry_points(group="ddoc")]
    assert "ddoc_categorical" in found, f"got: {found}"


# ── e2e via /analyze/drift HTTP route ───────────────────────────────


fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def http_client():
    os.environ.pop("DDOC_API_KEY", None)
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0"))


def test_analyze_drift_categorical_e2e(http_client: TestClient, tmp_path: Path):
    """Confirm that ``/analyze/drift`` picks up the categorical plugin
    when distributions.json files are present at both data paths."""
    ref, cur = _shifted_pair(tmp_path)
    r = http_client.post(
        "/analyze/drift",
        json={"data_path_ref": str(ref), "data_path_cur": str(cur),
              "quiet": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # The CLI may emit per-modality envelopes; categorical should be
    # one of them. Accept either single-envelope or multi-modality
    # stack shapes.
    if "modalities" in body:
        modalities = body["modalities"]
        assert "categorical" in modalities, modalities
        assert modalities["categorical"]["overall_score"] > 0.0
    else:
        assert body.get("modality") == "categorical"
        assert body.get("overall_score", 0) > 0.0
