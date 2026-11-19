# tests/conftest.py
# Purpose: shared pytest fixtures for CLI tests

import os
import shutil
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ddoc.cli.main import app

@pytest.fixture()
def runner():
    """Typer CLI test runner."""
    return CliRunner(mix_stderr=False)

@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    """
    Create and chdir into an isolated temp directory per test.
    Ensures files like report.json are written locally and compared deterministically.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(cwd)

@pytest.fixture()
def app_obj():
    """Expose the Typer app instance."""
    return app

@pytest.fixture()
def golden_dir():
    """Path to golden snapshot directory."""
    return Path(__file__).parent / "golden"

@pytest.fixture()
def freeze_time(monkeypatch):
    """
    Patch time.time used by builtins so EDA reports are deterministic.
    """
    import ddoc.builtin_plugins.builtin_impls as builtins_mod
    monkeypatch.setattr(builtins_mod.time, "time", lambda: 1234567890.0)
    return 1234567890.0