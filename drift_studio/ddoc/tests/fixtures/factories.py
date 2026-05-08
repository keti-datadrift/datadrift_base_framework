"""Toy-data factories — single source for both pytest fixtures and the
``ddoc examples generate`` user-facing CLI.

Round 11 (Track A) — Round 2~10 generated these datasets ad-hoc in
``/tmp`` during dev rounds; this module promotes them to permanent
factories so the same code path drives:

* the regression test suite (``tests/test_plugin_drift_e2e.py``), and
* the user onboarding command (``ddoc examples generate <modality>``).

Each factory writes a single dataset directory containing the file(s)
the relevant ddoc plugin expects plus a ``ddoc.yaml`` declaring
modality. Pair-of-(ref, cur) construction lives one level up
(``conftest.py`` fixtures and the ``ddoc examples`` command), keeping
factories themselves narrow and reusable.
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path
from typing import Any, Dict, Tuple


def _write_yaml(path: Path, fields: Dict[str, Any]) -> None:
    """Tiny YAML writer — stays free of pyyaml so factories work even in
    the lightest install (PyYAML is in core deps but tests run before
    it's necessarily imported)."""
    lines = []
    for key, value in fields.items():
        if isinstance(value, list):
            inner = ", ".join(str(v) for v in value)
            lines.append(f"{key}: [{inner}]")
        else:
            lines.append(f"{key}: {value}")
    path.write_text("\n".join(lines) + "\n")


# ── Timeseries ────────────────────────────────────────────────────────


def make_toy_timeseries(
    out_dir: str | Path,
    *,
    n: int = 200,
    mean: float = 0.0,
    std: float = 1.0,
    seed: int = 42,
    dataset_name: str = "toy_ts",
) -> Path:
    """Write a tiny timeseries dataset (CSV + ddoc.yaml) under
    ``<out_dir>/<dataset_name>/``.

    Schema: ``timestamp,x,y`` where ``x ~ N(mean, std)`` and
    ``y ~ N(0, 1)``. Returns the dataset directory.
    """
    rng = random.Random(seed)
    base = Path(out_dir)
    dataset_dir = base / dataset_name
    dataset_dir.mkdir(parents=True, exist_ok=True)

    csv_path = dataset_dir / "data.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "x", "y"])
        for i in range(n):
            w.writerow([i, rng.gauss(mean, std), rng.gauss(0.0, 1.0)])

    _write_yaml(
        dataset_dir / "ddoc.yaml",
        {
            "modality": "timeseries",
            "csv_file": "data.csv",
            "timestamp_column": "timestamp",
            "numeric_columns": ["x", "y"],
        },
    )
    return dataset_dir


# ── Audio ─────────────────────────────────────────────────────────────


def make_toy_audio(
    out_dir: str | Path,
    *,
    freq: float = 440.0,
    sr: int = 8000,
    duration: float = 1.0,
    amplitude: float = 0.3,
    dataset_name: str = "toy_audio",
) -> Path:
    """Write a tiny single-tone WAV (sine at ``freq`` Hz) + ddoc.yaml
    under ``<out_dir>/<dataset_name>/``.

    Soundfile and numpy are imported lazily because the audio plugin
    isn't always installed; callers needing audio fixtures install
    ``ddoc-plugin-audio`` first (which already pulls librosa/numpy).
    """
    import numpy as np
    import soundfile as sf

    base = Path(out_dir)
    dataset_dir = base / dataset_name
    dataset_dir.mkdir(parents=True, exist_ok=True)

    n_samples = int(sr * duration)
    t = np.linspace(0.0, duration, n_samples, endpoint=False)
    wave = amplitude * np.sin(2.0 * math.pi * freq * t)
    sf.write(str(dataset_dir / "tone.wav"), wave, sr)

    _write_yaml(
        dataset_dir / "ddoc.yaml",
        {"modality": "audio", "formats": [".wav"]},
    )
    return dataset_dir


# ── Text ──────────────────────────────────────────────────────────────


_VOCAB_SHORT = ["yes", "ok", "good", "fine", "thanks", "great", "nice", "sure"]
_VOCAB_LONG = [
    "The quick brown fox jumps over the lazy dog repeatedly throughout the day in the meadow.",
    "Comprehensive analysis indicates significant divergence between observed and expected outcomes here.",
    "Implementation of the algorithm requires careful consideration of memory constraints and threading.",
    "Subsequently, the proposed methodology demonstrates substantial improvements over baseline approaches.",
]


def make_toy_text(
    out_dir: str | Path,
    *,
    vocab: str = "short",
    n: int = 20,
    seed: int = 42,
    dataset_name: str = "toy_text",
) -> Path:
    """Write a tiny text dataset (CSV with id,text columns) +
    ddoc.yaml under ``<out_dir>/<dataset_name>/``.

    ``vocab`` selects the pool: ``"short"`` for terse one-word strings
    (low avg length, low vocabulary diversity) or ``"long"`` for
    multi-clause sentences. Pairing short-vs-long is the canonical
    drift scenario for the text plugin.
    """
    if vocab not in ("short", "long"):
        raise ValueError(f"vocab must be 'short' or 'long', got {vocab!r}")
    pool = _VOCAB_SHORT if vocab == "short" else _VOCAB_LONG

    rng = random.Random(seed)
    base = Path(out_dir)
    dataset_dir = base / dataset_name
    dataset_dir.mkdir(parents=True, exist_ok=True)

    csv_path = dataset_dir / "data.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "text"])
        for i in range(n):
            w.writerow([i, rng.choice(pool)])

    _write_yaml(
        dataset_dir / "ddoc.yaml",
        {
            "modality": "text",
            "text_column": "text",
            "id_column": "id",
            "language": "english",
        },
    )
    return dataset_dir


# ── Vision ────────────────────────────────────────────────────────────


def make_toy_vision(
    out_dir: str | Path,
    *,
    color: Tuple[int, int, int] = (255, 0, 0),
    n: int = 5,
    size: int = 64,
    dataset_name: str = "toy_vision",
) -> Path:
    """Write ``n`` solid-colour PNGs + ddoc.yaml under
    ``<out_dir>/<dataset_name>/``.

    Pillow is imported lazily; callers needing vision fixtures install
    ``ddoc-plugin-vision`` first (which pulls Pillow and friends).
    """
    from PIL import Image

    base = Path(out_dir)
    dataset_dir = base / dataset_name
    dataset_dir.mkdir(parents=True, exist_ok=True)

    for i in range(n):
        Image.new("RGB", (size, size), color).save(dataset_dir / f"img_{i}.png")

    _write_yaml(
        dataset_dir / "ddoc.yaml",
        {"modality": "image", "formats": [".png"]},
    )
    return dataset_dir


# ── Pair builders (the user-facing scenario level) ────────────────────


_REF_DIR = "ref"
_CUR_DIR = "cur"


def make_pair_timeseries(out_dir: str | Path, *, scenario: str = "shifted") -> Tuple[Path, Path]:
    """Return ``(ref_dir, cur_dir)`` for a timeseries drift scenario.

    ``scenario="shifted"``: ref ~ N(0, 1), cur ~ N(1.5, 1) — clear drift.
    ``scenario="identical"``: ref and cur both ~ N(0, 1) with same seed
    — drift score should be near-zero (sanity check).
    """
    base = Path(out_dir)
    if scenario == "shifted":
        ref = make_toy_timeseries(base / _REF_DIR, mean=0.0, seed=42)
        cur = make_toy_timeseries(base / _CUR_DIR, mean=1.5, seed=43)
    elif scenario == "identical":
        ref = make_toy_timeseries(base / _REF_DIR, mean=0.0, seed=42)
        cur = make_toy_timeseries(base / _CUR_DIR, mean=0.0, seed=42)
    else:
        raise ValueError(f"unsupported scenario: {scenario!r}")
    return base / _REF_DIR, base / _CUR_DIR


def make_pair_audio(out_dir: str | Path, *, scenario: str = "shifted") -> Tuple[Path, Path]:
    """Return ``(ref_dir, cur_dir)`` for an audio drift scenario.

    ``scenario="shifted"``: 440 Hz vs 880 Hz (octave apart — clear
    spectral drift). ``scenario="identical"``: both 440 Hz.
    """
    base = Path(out_dir)
    if scenario == "shifted":
        make_toy_audio(base / _REF_DIR, freq=440.0)
        make_toy_audio(base / _CUR_DIR, freq=880.0)
    elif scenario == "identical":
        make_toy_audio(base / _REF_DIR, freq=440.0)
        make_toy_audio(base / _CUR_DIR, freq=440.0)
    else:
        raise ValueError(f"unsupported scenario: {scenario!r}")
    return base / _REF_DIR, base / _CUR_DIR


def make_pair_text(out_dir: str | Path, *, scenario: str = "shifted") -> Tuple[Path, Path]:
    """Return ``(ref_dir, cur_dir)`` for a text drift scenario.

    ``scenario="shifted"``: ref uses the short vocab pool, cur uses
    the long sentences pool. ``scenario="identical"``: both short.
    """
    base = Path(out_dir)
    if scenario == "shifted":
        make_toy_text(base / _REF_DIR, vocab="short", seed=42)
        make_toy_text(base / _CUR_DIR, vocab="long", seed=43)
    elif scenario == "identical":
        make_toy_text(base / _REF_DIR, vocab="short", seed=42)
        make_toy_text(base / _CUR_DIR, vocab="short", seed=42)
    else:
        raise ValueError(f"unsupported scenario: {scenario!r}")
    return base / _REF_DIR, base / _CUR_DIR


def make_pair_vision(out_dir: str | Path, *, scenario: str = "shifted") -> Tuple[Path, Path]:
    """Return ``(ref_dir, cur_dir)`` for a vision drift scenario.

    ``scenario="shifted"``: 5 red 64×64 PNGs vs 5 blue. ``scenario=
    "identical"``: both red.
    """
    base = Path(out_dir)
    if scenario == "shifted":
        make_toy_vision(base / _REF_DIR, color=(255, 0, 0))
        make_toy_vision(base / _CUR_DIR, color=(0, 0, 255))
    elif scenario == "identical":
        make_toy_vision(base / _REF_DIR, color=(255, 0, 0))
        make_toy_vision(base / _CUR_DIR, color=(255, 0, 0))
    else:
        raise ValueError(f"unsupported scenario: {scenario!r}")
    return base / _REF_DIR, base / _CUR_DIR


# Index for the ``ddoc examples`` CLI to enumerate.
PAIR_BUILDERS = {
    "timeseries": make_pair_timeseries,
    "audio": make_pair_audio,
    "text": make_pair_text,
    "vision": make_pair_vision,
}

SUPPORTED_SCENARIOS = ("shifted", "identical")
