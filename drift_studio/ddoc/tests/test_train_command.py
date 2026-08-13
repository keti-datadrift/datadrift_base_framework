"""Round 16-D (alpr R21) — unit tests for the `ddoc train` CLI.

Exercises argv parsing, --params-json validation, plugin fan-out
(via a fake plugin), and the JSON envelope output mode.
"""
from __future__ import annotations

import json
import io
import sys
from types import SimpleNamespace
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from ddoc.cli.commands.train import train_command


def _run(args, *, mock_pm):
    """Invoke train_command with a mocked plugin manager.

    Uses a Typer test runner so we can capture stdout / exit code
    cleanly.
    """
    import typer
    app = typer.Typer()
    app.command()(train_command)

    runner = CliRunner()
    # Inject the mocked plugin manager.
    import ddoc.cli.commands.train as train_mod

    def _get_pmgr():
        return SimpleNamespace(pm=mock_pm)

    orig = train_mod.get_pmgr
    train_mod.get_pmgr = _get_pmgr
    try:
        return runner.invoke(app, args)
    finally:
        train_mod.get_pmgr = orig


def _make_pm(responses):
    """Build a fake plugin manager whose hook.retrain_run returns the
    given list of plugin responses (Nones for "not mine")."""
    pm = MagicMock()
    pm.hook.retrain_run.return_value = responses
    return pm


# ── happy path ──────────────────────────────────────────────────


def test_train_command_emits_first_envelope_as_json():
    envelope = {
        "status": "ok",
        "trainer": "alpr-recognizer",
        "model_path": "/runs/best.pth",
        "metrics": {"new_accuracy": 0.91},
        "duration_sec": 1.5,
        "gate_passed": True,
    }
    pm = _make_pm([None, envelope, None])  # one plugin claims it
    res = _run(
        [
            "--train-path", "/data",
            "--trainer", "alpr-recognizer",
            "--model-out", "/runs",
            "--params-json", json.dumps({"epochs": 1}),
            "--json",
        ],
        mock_pm=pm,
    )
    assert res.exit_code == 0
    out = json.loads(res.stdout.strip())
    assert out["status"] == "ok"
    assert out["model_path"] == "/runs/best.pth"
    # Verify the plugin received the right kwargs.
    pm.hook.retrain_run.assert_called_once()
    kwargs = pm.hook.retrain_run.call_args.kwargs
    assert kwargs["trainer"] == "alpr-recognizer"
    assert kwargs["params"] == {"epochs": 1}


def test_train_command_unknown_trainer_emits_envelope_with_code_2():
    """When no plugin claims the trainer, exit code 2 + envelope."""
    pm = _make_pm([None, None])  # everyone says "not mine"
    res = _run(
        [
            "--train-path", "/data",
            "--trainer", "no-such-trainer",
            "--params-json", "{}",
            "--json",
        ],
        mock_pm=pm,
    )
    assert res.exit_code == 2
    out = json.loads(res.stdout.strip())
    assert out["status"] == "error"
    assert out["error_code"] == "unknown_trainer"


def test_train_command_bad_params_json_exits_2():
    pm = _make_pm([])
    res = _run(
        [
            "--train-path", "/data",
            "--trainer", "alpr-recognizer",
            "--params-json", "not-valid-json",
            "--json",
        ],
        mock_pm=pm,
    )
    assert res.exit_code == 2
    out = json.loads(res.stdout.strip())
    assert out["error_code"] == "bad_params_json"


def test_train_command_passes_through_error_envelope_with_code_1():
    """Plugin returned status=error → exit 1 + envelope on stdout."""
    envelope = {
        "status": "error",
        "trainer": "alpr-recognizer",
        "message": "CUDA OOM",
    }
    pm = _make_pm([envelope])
    res = _run(
        [
            "--train-path", "/data",
            "--trainer", "alpr-recognizer",
            "--params-json", "{}",
            "--json",
        ],
        mock_pm=pm,
    )
    assert res.exit_code == 1
    out = json.loads(res.stdout.strip())
    assert out["status"] == "error"
    assert "CUDA OOM" in out["message"]
