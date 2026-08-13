"""Round 49 (alpr-paired) — unit tests for the `ddoc transform` CLI.

Exercises argv parsing, --args-json validation, plugin fan-out (via a
fake plugin), and JSON envelope emission. Mirrors test_train_command.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from typer.testing import CliRunner

from ddoc.cli.commands.transform import transform_command


def _run(args, *, mock_pm):
    import typer
    app = typer.Typer()
    app.command()(transform_command)

    runner = CliRunner()
    import ddoc.cli.commands.transform as mod

    def _get_pmgr():
        return SimpleNamespace(pm=mock_pm)

    orig = mod.get_pmgr
    mod.get_pmgr = _get_pmgr
    try:
        return runner.invoke(app, args)
    finally:
        mod.get_pmgr = orig


def _make_pm(responses):
    pm = MagicMock()
    pm.hook.transform_apply.return_value = responses
    return pm


# ── happy path ──────────────────────────────────────────────────


def test_transform_command_emits_first_envelope_as_json():
    envelope = {
        "status": "ok",
        "transform": "pii_blur",
        "output_path": "/out",
        "result": {"images_processed": 8, "crops_saved": 10},
    }
    pm = _make_pm([None, envelope, None])
    res = _run(
        [
            "--input-path", "/in",
            "--transform", "pii_blur",
            "--output-path", "/out",
            "--args-json", json.dumps({"blur_kernel": 31}),
            "--json",
        ],
        mock_pm=pm,
    )
    assert res.exit_code == 0, res.stdout
    out = json.loads(res.stdout.strip())
    assert out["status"] == "ok"
    assert out["transform"] == "pii_blur"
    pm.hook.transform_apply.assert_called_once()
    kwargs = pm.hook.transform_apply.call_args.kwargs
    assert kwargs["transform"] == "pii_blur"
    assert kwargs["args"] == {"blur_kernel": 31}


def test_transform_command_unknown_transform_exits_2():
    pm = _make_pm([None, None])
    res = _run(
        [
            "--input-path", "/in",
            "--transform", "no-such",
            "--output-path", "/out",
            "--args-json", "{}",
            "--json",
        ],
        mock_pm=pm,
    )
    assert res.exit_code == 2
    out = json.loads(res.stdout.strip())
    assert out["error_code"] == "unknown_transform"


def test_transform_command_bad_args_json_exits_2():
    pm = _make_pm([])
    res = _run(
        [
            "--input-path", "/in",
            "--transform", "pii_blur",
            "--output-path", "/out",
            "--args-json", "not-valid-json",
            "--json",
        ],
        mock_pm=pm,
    )
    assert res.exit_code == 2
    out = json.loads(res.stdout.strip())
    assert out["error_code"] == "bad_args_json"


def test_transform_command_passes_through_error_envelope_with_code_1():
    envelope = {
        "status": "error",
        "transform": "pii_blur",
        "message": "disk full",
    }
    pm = _make_pm([envelope])
    res = _run(
        [
            "--input-path", "/in",
            "--transform", "pii_blur",
            "--output-path", "/out",
            "--args-json", "{}",
            "--json",
        ],
        mock_pm=pm,
    )
    assert res.exit_code == 1
    out = json.loads(res.stdout.strip())
    assert out["status"] == "error"
    assert "disk full" in out["message"]


# ── step kind registration ──────────────────────────────────────


def test_recipe_step_kind_transform_registered():
    """The recipe runner must know about ``run: transform`` so that
    YAML recipes can use it. The new entry mirrors ``train``."""
    from ddoc.core.recipe import _STEP_KINDS
    assert "transform" in _STEP_KINDS
    spec = _STEP_KINDS["transform"]
    assert spec["argv"] == ["transform"]
    assert spec["options"]["transform"] == "--transform"
    assert spec["options"]["args"] == "--args-json"
    assert spec["json_flag"] is True
