"""Pytest fixtures for ddoc tests.

Round 11 (Track A) — additive new conftest. The legacy
``__conftest.py`` (with double-underscore disabled prefix) stays
parked. This file exposes the ``tests/fixtures/factories.py`` toy-data
generators as ready-to-use ``(ref, cur)`` pair fixtures so plugin
end-to-end tests stay terse.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pytest

import sys as _sys
from pathlib import Path as _Path

# pytest adds the conftest.py directory to ``sys.path`` only when the
# tree is a package; this is an *additive* conftest (the legacy
# ``__conftest.py`` is still parked) so we make ``fixtures`` importable
# explicitly without forcing a top-level ``tests/__init__.py``.
_sys.path.insert(0, str(_Path(__file__).parent))

from fixtures.factories import (  # noqa: E402
    make_pair_timeseries,
    make_pair_audio,
    make_pair_text,
    make_pair_vision,
)


@pytest.fixture
def toy_timeseries_pair(tmp_path: Path) -> Tuple[Path, Path]:
    """Shifted timeseries pair (ref ~ N(0,1), cur ~ N(1.5,1))."""
    return make_pair_timeseries(tmp_path, scenario="shifted")


@pytest.fixture
def toy_timeseries_identical(tmp_path: Path) -> Tuple[Path, Path]:
    """Identical timeseries pair — for near-zero drift sanity checks."""
    return make_pair_timeseries(tmp_path, scenario="identical")


@pytest.fixture
def toy_audio_pair(tmp_path: Path) -> Tuple[Path, Path]:
    """Shifted audio pair (440 Hz ref vs 880 Hz cur)."""
    return make_pair_audio(tmp_path, scenario="shifted")


@pytest.fixture
def toy_audio_identical(tmp_path: Path) -> Tuple[Path, Path]:
    """Identical audio pair (both 440 Hz)."""
    return make_pair_audio(tmp_path, scenario="identical")


@pytest.fixture
def toy_text_pair(tmp_path: Path) -> Tuple[Path, Path]:
    """Shifted text pair (short vocab vs long sentences)."""
    return make_pair_text(tmp_path, scenario="shifted")


@pytest.fixture
def toy_text_identical(tmp_path: Path) -> Tuple[Path, Path]:
    """Identical text pair (both short vocab)."""
    return make_pair_text(tmp_path, scenario="identical")


@pytest.fixture
def toy_vision_pair(tmp_path: Path) -> Tuple[Path, Path]:
    """Shifted vision pair (red imgs vs blue imgs)."""
    return make_pair_vision(tmp_path, scenario="shifted")


@pytest.fixture
def toy_vision_identical(tmp_path: Path) -> Tuple[Path, Path]:
    """Identical vision pair (both red)."""
    return make_pair_vision(tmp_path, scenario="identical")
