"""``ddoc train`` — invoke a plugin's training implementation.

R21 (alpr framework consolidation) — thin CLI wrapper around the
``retrain_run`` hookspec (declared in ``ddoc.plugins.hookspecs:91``).
Plugins responding to ``trainer=<name>`` perform the actual training;
this command captures the first non-None envelope returned and emits
it as JSON.

The companion recipe step is the ``train`` kind registered in
``ddoc/core/recipe.py:_STEP_KINDS`` — recipes invoke this command via
the recipe runner's subprocess transport.

Example:

    ddoc train \\
      --train-path data/full_train \\
      --trainer alpr-recognizer \\
      --model-out runs/dd_train \\
      --params-json '{"epochs": 5, "batch": 64, "device": "cpu"}' \\
      --json
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

import typer
from rich import print as rprint

from .utils import get_pmgr


def train_command(
    train_path: str = typer.Option(
        ..., "--train-path",
        help="Path to training data (directory or trainer-specific file).",
    ),
    trainer: str = typer.Option(
        ..., "--trainer",
        help="Trainer name claimed by an installed plugin (e.g. alpr-recognizer, "
             "alpr-detector, yolo).",
    ),
    model_out: str = typer.Option(
        "", "--model-out",
        help="Output directory for model artifacts. Plugin-specific layout.",
    ),
    params_json: Optional[str] = typer.Option(
        None, "--params-json",
        help='Trainer parameters as JSON (e.g. \'{"epochs": 50, "batch": 64}\').',
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit a single-line JSON envelope instead of pretty output.",
    ),
):
    """Run a plugin's ``retrain_run`` hook for the named trainer.

    Plugins that don't own the trainer return None; ddoc collects all
    responses and picks the first non-None envelope. If no plugin
    claims the trainer, exits with code 2 and emits an
    ``unknown_trainer`` envelope.
    """
    params: Dict[str, Any] = {}
    if params_json:
        try:
            params = json.loads(params_json)
            if not isinstance(params, dict):
                raise ValueError("--params-json must decode to an object")
        except (json.JSONDecodeError, ValueError) as e:
            err = {
                "status": "error",
                "error_code": "bad_params_json",
                "message": f"--params-json must be a valid JSON object: {e}",
            }
            _emit(err, json_out)
            raise typer.Exit(code=2)

    pm = get_pmgr().pm
    try:
        responses = pm.hook.retrain_run(
            train_path=train_path,
            trainer=trainer,
            params=params,
            model_out=model_out,
        )
    except Exception as e:  # noqa: BLE001 — plugin raised, surface as envelope
        err = {
            "status": "error",
            "error_code": "plugin_exception",
            "trainer": trainer,
            "message": f"plugin raised during retrain_run: {type(e).__name__}: {e}",
        }
        _emit(err, json_out)
        raise typer.Exit(code=1)

    # Hook fan-out: list of results. Filter out plugin "not mine" Nones.
    envelopes = [r for r in (responses or []) if r is not None]
    if not envelopes:
        err = {
            "status": "error",
            "error_code": "unknown_trainer",
            "trainer": trainer,
            "message": (
                f"no installed plugin claims trainer={trainer!r}. "
                f"Install a plugin that implements retrain_run for this "
                f"trainer name."
            ),
        }
        _emit(err, json_out)
        raise typer.Exit(code=2)

    # If multiple plugins responded, the first wins. (pluggy returns
    # results in registration order, last-registered-first by default.)
    result = envelopes[0]

    _emit(result, json_out)
    status = (result.get("status") if isinstance(result, dict) else None) or "ok"
    if status == "error":
        raise typer.Exit(code=1)


def _emit(payload: Dict[str, Any], json_out: bool) -> None:
    if json_out:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        sys.stdout.flush()
    else:
        if payload.get("status") == "error":
            rprint(f"[red]❌ {payload.get('message', payload)}[/red]")
        else:
            rprint(f"[green]✅ trainer={payload.get('trainer')} "
                   f"model_path={payload.get('model_path')}[/green]")
            metrics = payload.get("metrics") or {}
            for k, v in metrics.items():
                rprint(f"   {k}: {v}")
