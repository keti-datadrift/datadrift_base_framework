"""End-to-end drift tests, one per modality, exercising the full CLI
path through the orchestrator pivot (--json envelope on stdout, NDJSON
progress on stderr, plugin path-mode contract).

Round 11 (Track A) — these replace the ad-hoc /tmp/toy_* scenarios we
ran by hand during Round 2~10. Each test:

1. Builds a (ref, cur) pair via the factory fixtures (conftest.py).
2. Forks ``python -m ddoc.cli.main analyze drift --data-path-ref/-cur
   --json --quiet`` (hermetic invocation; --quiet keeps plugin chatter
   off stderr so any failure tail is readable).
3. Parses stdout as the contract envelope and asserts:
   - exit 0
   - ``modality`` field is set to the expected value
   - ``overall_score > 0`` for the "shifted" scenario
   - ``overall_score`` is small for the "identical" scenario
4. If the modality's plugin isn't installed, the test skips
   gracefully — Heavy CLIP/torch/librosa deps must not block the
   timeseries-only smoke pipeline.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

import pytest


def _plugin_installed(name: str) -> bool:
    """Best-effort check that an entry-point with this name is
    registered in the current interpreter."""
    try:
        import importlib.metadata as md
    except ImportError:  # pragma: no cover
        return False
    try:
        eps = md.entry_points(group="ddoc")
    except Exception:
        return False
    for ep in eps:
        if ep.name == name:
            return True
    return False


def _parse_last_json_object(text: str) -> dict:
    """Return the last brace-balanced JSON object in ``text``.

    Mirrors backend's ``ddoc_runner._try_parse_last_json_object`` —
    needed because some plugins emit summary banners alongside the
    envelope even with --quiet. Naive ``rfind("{")`` jumps into nested
    objects and trips ``Extra data`` errors.
    """
    s = text.strip()
    if not s:
        raise ValueError("empty stdout")
    if s.startswith("{") and s.endswith("}"):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    depth = 0
    end = -1
    for i in range(len(s) - 1, -1, -1):
        ch = s[i]
        if ch == "}":
            if end == -1:
                end = i
            depth += 1
        elif ch == "{":
            depth -= 1
            if depth == 0:
                candidate = s[i:end + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    end = -1
                    depth = 0
                    continue
    raise ValueError(f"no parseable JSON object in stdout: {text[:200]!r}")


def _run_drift(ref: Path, cur: Path) -> dict:
    """Invoke the CLI in path mode and return the parsed envelope."""
    cmd = [
        sys.executable, "-m", "ddoc.cli.main",
        "analyze", "drift",
        "--data-path-ref", str(ref),
        "--data-path-cur", str(cur),
        "--json", "--quiet",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, (
        f"ddoc analyze drift exit={proc.returncode}\n"
        f"stderr tail:\n{proc.stderr[-1000:]}"
    )
    return _parse_last_json_object(proc.stdout)


# ── Timeseries — always runs (lightweight stats only) ─────────────────


def test_drift_timeseries_shifted(toy_timeseries_pair: Tuple[Path, Path]):
    if not _plugin_installed("ddoc_timeseries"):
        pytest.skip("ddoc-plugin-timeseries not installed")
    ref, cur = toy_timeseries_pair
    res = _run_drift(ref, cur)
    assert res.get("modality") == "timeseries"
    assert res.get("overall_score", 0) > 0.05, res


def test_drift_timeseries_identical(toy_timeseries_identical: Tuple[Path, Path]):
    if not _plugin_installed("ddoc_timeseries"):
        pytest.skip("ddoc-plugin-timeseries not installed")
    ref, cur = toy_timeseries_identical
    res = _run_drift(ref, cur)
    assert res.get("modality") == "timeseries"
    # Identical seed → identical means/var/skew/kurt → score == 0.
    assert res.get("overall_score", 1.0) < 1e-6, res


# ── Audio — needs ddoc-plugin-audio + librosa ─────────────────────────


def test_drift_audio_shifted(toy_audio_pair: Tuple[Path, Path]):
    if not _plugin_installed("ddoc_audio"):
        pytest.skip("ddoc-plugin-audio not installed")
    ref, cur = toy_audio_pair
    res = _run_drift(ref, cur)
    assert res.get("modality") == "audio"
    # 440Hz → 880Hz spectral_centroid difference is large.
    assert res.get("overall_score", 0) > 1.0, res


def test_drift_audio_identical(toy_audio_identical: Tuple[Path, Path]):
    if not _plugin_installed("ddoc_audio"):
        pytest.skip("ddoc-plugin-audio not installed")
    ref, cur = toy_audio_identical
    res = _run_drift(ref, cur)
    assert res.get("modality") == "audio"
    # Same waveform → wasserstein on identical distributions ≈ 0.
    assert res.get("overall_score", 1.0) < 1e-6, res


# ── Text — needs ddoc-plugin-text + nltk data ─────────────────────────


def _nltk_ready() -> bool:
    try:
        import nltk
        nltk.data.find("tokenizers/punkt_tab")
        return True
    except Exception:
        return False


def test_drift_text_shifted(toy_text_pair: Tuple[Path, Path]):
    if not _plugin_installed("ddoc_text"):
        pytest.skip("ddoc-plugin-text not installed")
    if not _nltk_ready():
        pytest.skip("nltk punkt_tab not downloaded — run nltk.download('punkt_tab')")
    ref, cur = toy_text_pair
    res = _run_drift(ref, cur)
    assert res.get("modality") == "text"
    # Short vs long sentences — length-based attribute drift dominates.
    assert res.get("overall_score", 0) > 0.5, res


def test_drift_text_identical(toy_text_identical: Tuple[Path, Path]):
    if not _plugin_installed("ddoc_text"):
        pytest.skip("ddoc-plugin-text not installed")
    if not _nltk_ready():
        pytest.skip("nltk punkt_tab not downloaded")
    ref, cur = toy_text_identical
    res = _run_drift(ref, cur)
    assert res.get("modality") == "text"
    assert res.get("overall_score", 1.0) < 1e-6, res


# ── Vision — needs ddoc-plugin-vision + torch + CLIP ──────────────────


def test_drift_vision_shifted(toy_vision_pair: Tuple[Path, Path]):
    if not _plugin_installed("ddoc_vision"):
        pytest.skip("ddoc-plugin-vision not installed")
    ref, cur = toy_vision_pair
    res = _run_drift(ref, cur)
    # Vision plugin returns its own envelope shape; confirm a drift was
    # detected. ``overall_score`` is bounded [0, 1] for the ensemble,
    # red↔blue is firmly nonzero.
    assert res.get("overall_score", 0) > 0.05, res


def test_drift_vision_identical(toy_vision_identical: Tuple[Path, Path]):
    if not _plugin_installed("ddoc_vision"):
        pytest.skip("ddoc-plugin-vision not installed")
    ref, cur = toy_vision_identical
    res = _run_drift(ref, cur)
    # Same colour → near-zero drift. Threshold is loose because the
    # plugin's PCA-PSI stage can produce small numerical jitter.
    assert res.get("overall_score", 1.0) < 0.1, res
