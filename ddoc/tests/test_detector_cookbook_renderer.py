"""Round 15 — detector cookbook auto-renderer tests.

The renderer (`scripts/render_detector_cookbook.py`) shells out to
`ddoc examples generate` + `ddoc analyze drift --json`. Tests
exercise both the pure-function render helpers (no subprocess) and
the e2e path (one full `categorical` render, marked as integration
to keep the suite under control).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from scripts.render_detector_cookbook import (
    _DETECTOR_SETS,
    main,
    render_table,
    run,
)


# ── render_table is pure ──────────────────────────────────────────


def test_render_table_includes_modality_heading():
    body = render_table("categorical", [("default", 0.11), ("overlap", 0.25)])
    assert "### `categorical` modality" in body
    assert "default" in body and "overlap" in body
    assert "0.1100" in body and "0.2500" in body


def test_render_table_renders_dash_for_missing_scores():
    body = render_table("categorical", [("default", None)])
    assert "—" in body
    assert "skipped" in body


# ── detector sets stay in sync with the cookbook ──────────────────


def test_categorical_detector_set_documented():
    assert set(_DETECTOR_SETS["categorical"]) == {
        "default", "jensen_shannon", "overlap",
    }


def test_image_detector_set_documented():
    assert set(_DETECTOR_SETS["image"]) >= {
        "ensemble", "mmd", "wasserstein", "psi",
    }


# ── e2e renderer (categorical only — fast) ────────────────────────


def test_renderer_run_categorical_produces_a_table(tmp_path):
    """Full e2e: invoke `run()`, which shells out to the real CLI.
    Skipped if `ddoc` isn't on PATH (system pytest invocation without
    venv activation — bash 12_pytest.sh self-activates so CI is fine)."""
    if shutil.which("ddoc") is None:
        pytest.skip("ddoc CLI not on PATH")
    body = run(["categorical"])
    assert "categorical" in body
    # The shifted demo always yields a non-zero score with the default
    # detector — if it doesn't, the demo data path or the plugin
    # changed and the cookbook needs review.
    assert "0.0000" not in body


def test_main_writes_output_file(tmp_path):
    """`main()` writes the generated table to the configured path."""
    if shutil.which("ddoc") is None:
        pytest.skip("ddoc CLI not on PATH")
    out_path = tmp_path / "scores.md"
    rc = main(["--modalities", "categorical", "--out", str(out_path)])
    assert rc == 0
    assert out_path.is_file()
    body = out_path.read_text(encoding="utf-8")
    assert "Auto-generated" in body
    assert "categorical" in body
    assert "overall_score" in body
