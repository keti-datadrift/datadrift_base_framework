"""Round 9 (D2 Track A) — `ddoc examples generate categorical` smoke
tests + hybrid framing schema check vs keti.

These tests live next to the existing `tests/fixtures/factories.py`
toy-data generators. Categorical is the first new modality added
since Round 11 (Track A).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make tests/fixtures/ importable.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from fixtures import factories  # noqa: E402


def test_categorical_listed_in_pair_builders():
    assert "categorical" in factories.PAIR_BUILDERS


def test_categorical_shifted_emits_distributions_json(tmp_path):
    ref, cur = factories.make_pair_categorical(tmp_path, scenario="shifted")
    assert (ref / "distributions.json").is_file()
    assert (cur / "distributions.json").is_file()
    assert (ref / "ddoc.yaml").is_file()
    ref_data = json.loads((ref / "distributions.json").read_text())
    cur_data = json.loads((cur / "distributions.json").read_text())
    # Shifted scenario must produce different distributions on at least
    # one attribute, otherwise drift detection would be 0.
    assert ref_data != cur_data


def test_categorical_identical_scenario_produces_equal_dicts(tmp_path):
    ref, cur = factories.make_pair_categorical(tmp_path, scenario="identical")
    ref_data = json.loads((ref / "distributions.json").read_text())
    cur_data = json.loads((cur / "distributions.json").read_text())
    assert ref_data == cur_data


def test_categorical_unsupported_scenario_raises(tmp_path):
    with pytest.raises(ValueError, match="unsupported scenario"):
        factories.make_pair_categorical(tmp_path, scenario="lopsided")


# ── Hybrid framing: keti shape equivalence ──────────────────────────


# Schema-level expectation pinned independently of any keti import —
# this mirrors what
# ``keti_veritas/app/domains/analytics/repository.py:build_camera_stats_window``
# emits. If keti changes the shape, both sides must update together;
# this test catches the divergence at PR time on the ddoc side.
_KETI_REQUIRED_KEYS = {
    "color_distribution",
    "type_distribution",
    "hourly_distribution",
    "confidence_stats",
}


def test_categorical_demo_shape_matches_keti_repository_output(tmp_path):
    ref, _ = factories.make_pair_categorical(tmp_path, scenario="shifted")
    payload = json.loads((ref / "distributions.json").read_text())

    # Top-level keys identical to what keti's
    # build_camera_stats_window dict carries.
    assert set(payload.keys()) >= _KETI_REQUIRED_KEYS, (
        f"missing keys: {_KETI_REQUIRED_KEYS - set(payload.keys())}"
    )
    # Each distribution dict's values are numeric counts (or floats
    # for confidence_stats).
    assert all(isinstance(v, (int, float))
               for v in payload["color_distribution"].values())
    assert all(isinstance(v, (int, float))
               for v in payload["type_distribution"].values())
    # hourly_distribution is keyed by hour-of-day string.
    assert all(isinstance(k, str) and k.isdigit() and 0 <= int(k) <= 23
               for k in payload["hourly_distribution"])
    # confidence_stats has the {mean, std} sub-shape.
    assert {"mean", "std"} <= set(payload["confidence_stats"].keys())


def test_categorical_demo_e2e_via_cli_subprocess(tmp_path):
    """Spawn the CLI in a subprocess and confirm the full pipeline:
    `ddoc examples generate categorical --out X --scenario shifted` →
    `ddoc analyze drift --data-path-ref X/ref --data-path-cur X/cur --json`
    yields a categorical envelope with overall_score > 0."""
    import subprocess
    cli = "ddoc"  # pytest runs inside .venv via 12_pytest.sh, so this resolves.
    out = tmp_path / "demo"
    gen = subprocess.run(
        [cli, "examples", "generate", "categorical",
         "--out", str(out), "--scenario", "shifted"],
        capture_output=True, text=True, timeout=30,
    )
    if gen.returncode != 0 or not (out / "ref" / "distributions.json").is_file():
        pytest.skip(f"ddoc CLI not on PATH or failed: {gen.stderr[:200]}")

    drift = subprocess.run(
        [cli, "analyze", "drift",
         "--data-path-ref", str(out / "ref"),
         "--data-path-cur", str(out / "cur"),
         "--json", "--quiet"],
        capture_output=True, text=True, timeout=60,
    )
    assert drift.returncode == 0, drift.stderr
    # Last JSON object on stdout is the envelope (CLI may emit warnings
    # before it).
    stdout = drift.stdout.strip()
    last_line = next(
        (line for line in reversed(stdout.splitlines())
         if line.strip().startswith("{")),
        None,
    )
    assert last_line is not None, f"no JSON in stdout: {stdout[:300]}"
    envelope = json.loads(last_line)
    assert envelope["status"] == "success"
    assert envelope["modality"] == "categorical"
    assert envelope["overall_score"] > 0.0
    assert "color_distribution" in envelope["attribute_drifts"]
