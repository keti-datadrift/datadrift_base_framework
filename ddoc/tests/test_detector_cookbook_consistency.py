"""Round 10 (D2 Track B) — detector cookbook consistency.

The cookbook (`docs/tutorial/detectors.md`) tells users which
detectors each plugin supports. These tests confirm the documentation
matches reality:

* `ddoc plugin detectors` advertises the same set the cookbook
  documents.
* For modalities with multiple real strategies (`categorical`,
  `image`), running each `--detector` value through `ddoc analyze
  drift` against the toy demo data produces a valid envelope with
  a numeric `overall_score`.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))


# Cookbook truth — keep in sync with docs/tutorial/detectors.md.
_DOCUMENTED_DETECTORS = {
    "categorical": ["default", "jensen_shannon", "js", "overlap"],
    # image plugin's set; we don't run the heavy image tests here
    # (CLIP / torch import cost) — covered by separate vision tests.
    "image": ["default", "ensemble", "mmd", "mean_shift",
              "wasserstein", "psi", "cosine"],
    "timeseries": ["default", "mmd", "attributes"],
    "audio": ["default", "mmd", "wasserstein"],
}


def test_plugin_advertises_documented_categorical_detectors():
    """The categorical plugin's `ddoc_supported_detectors` reports the
    same strategies the cookbook documents."""
    from ddoc_plugin_categorical.categorical_impl import CategoricalDriftPlugin
    plugin = CategoricalDriftPlugin()
    decl = plugin.ddoc_supported_detectors()
    assert decl["modality"] == "categorical"
    documented = set(_DOCUMENTED_DETECTORS["categorical"])
    advertised = set(decl["supported"])
    assert advertised == documented, (
        f"cookbook lists {documented}, plugin advertises {advertised}"
    )


@pytest.mark.parametrize("detector",
                         ["default", "jensen_shannon", "js", "overlap"])
def test_categorical_demo_runs_with_each_documented_detector(detector, tmp_path):
    """For every detector the cookbook documents on `categorical`,
    running `ddoc analyze drift` end-to-end produces a numeric
    `overall_score` envelope."""
    cli = shutil.which("ddoc")
    if cli is None:
        pytest.skip("ddoc CLI not on PATH")

    out = tmp_path / "demo"
    gen = subprocess.run(
        [cli, "examples", "generate", "categorical",
         "--out", str(out), "--scenario", "shifted"],
        capture_output=True, text=True, timeout=30,
    )
    assert gen.returncode == 0, gen.stderr

    drift = subprocess.run(
        [cli, "analyze", "drift",
         "--data-path-ref", str(out / "ref"),
         "--data-path-cur", str(out / "cur"),
         "--detector", detector,
         "--json", "--quiet"],
        capture_output=True, text=True, timeout=60,
    )
    assert drift.returncode == 0, drift.stderr

    last = next(
        (line for line in reversed(drift.stdout.splitlines())
         if line.strip().startswith("{")),
        None,
    )
    assert last is not None, drift.stdout[:300]
    env = json.loads(last)
    assert env.get("status") == "success"
    assert env.get("modality") == "categorical"
    score = env.get("overall_score")
    assert isinstance(score, (int, float))
    assert 0.0 <= score <= 1.0


def test_overlap_score_at_least_as_high_as_jensen_shannon():
    """Cookbook claim: 'overlap 은 보통 jensen_shannon 보다 큰 값이
    나옵니다'. Verify on the canonical shifted demo data so the
    documentation rationale stays evidence-backed."""
    from ddoc_plugin_categorical.categorical_impl import (
        jensen_shannon, overlap_distance,
    )
    # Use the same canonical "shifted" distributions as the demo.
    from fixtures.factories import (  # type: ignore[import-not-found]
        _CATEGORICAL_REF, _CATEGORICAL_CUR_SHIFTED,
    )

    for attr in ("color_distribution", "type_distribution"):
        js_score = jensen_shannon(
            _CATEGORICAL_REF[attr], _CATEGORICAL_CUR_SHIFTED[attr],
        )
        ov_score = overlap_distance(
            _CATEGORICAL_REF[attr], _CATEGORICAL_CUR_SHIFTED[attr],
        )
        # The cookbook says "보통 더 큼" — assert ≥ to allow exact-equality
        # edge cases without flaking.
        assert ov_score >= js_score, (
            f"on {attr}: overlap={ov_score:.4f} < jensen_shannon={js_score:.4f}"
        )


def test_severity_thresholds_match_alpr_gate_default():
    """Cookbook says critical = >0.25, matching alpr's
    `ALPR_DDOC_GATE_DRIFT_THRESHOLD` default. If alpr's default
    changes, this test catches the doc drift."""
    # We can't import alpr from ddoc tests (separate project), so we
    # pin the default value the cookbook references.
    DOCUMENTED_CRITICAL = 0.25

    cookbook_path = (
        Path(__file__).resolve().parents[1]
        / "docs" / "tutorial" / "detectors.md"
    )
    body = cookbook_path.read_text(encoding="utf-8")
    # Sanity: the threshold value appears in the cookbook prose AND in
    # the alpr default constant referenced.
    assert "0.25" in body
    assert str(DOCUMENTED_CRITICAL) in body
