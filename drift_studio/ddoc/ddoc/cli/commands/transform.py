"""``ddoc transform`` — invoke a plugin's ``transform_apply`` hook.

R49 (alpr PII/EDA plugin consolidation, paired with alpr R49) — thin
CLI wrapper around the ``transform_apply`` hookspec declared in
``ddoc.plugins.hookspecs``. Mirrors the ``ddoc train`` (R21) pattern:
plugins responding to ``transform=<name>`` perform the actual work
(e.g. ``ddoc-plugin-pii-eda`` claims ``transform=pii_blur``), and
this command captures the first non-None envelope and emits it as
JSON.

The companion recipe step is the ``transform`` kind registered in
``ddoc/core/recipe.py:_STEP_KINDS``.

Example:

    ddoc transform \\
      --input-path ./images \\
      --transform pii_blur \\
      --output-path ./anonymized \\
      --args-json '{"detector": "openimagemodels", "blur_kernel": 31}' \\
      --json
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

import typer
from rich import print as rprint

from .utils import get_pmgr


def transform_command(
    input_path: str = typer.Option(
        ..., "--input-path",
        help="Source path (file or directory) the transform reads from.",
    ),
    transform: str = typer.Option(
        ..., "--transform",
        help="Transform name claimed by an installed plugin (e.g. pii_blur).",
    ),
    output_path: str = typer.Option(
        ..., "--output-path",
        help="Destination path the transform writes to. Plugin-specific layout.",
    ),
    args_json: Optional[str] = typer.Option(
        None, "--args-json",
        help='Transform args as JSON (e.g. \'{"blur_kernel": 31}\').',
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit a single-line JSON envelope instead of pretty output.",
    ),
):
    """Run a plugin's ``transform_apply`` hook for the named transform.

    Plugins that don't own the transform return None; ddoc collects
    all responses and picks the first non-None envelope. If no plugin
    claims the transform, exits with code 2 and emits an
    ``unknown_transform`` envelope.
    """
    args: Dict[str, Any] = {}
    if args_json:
        try:
            args = json.loads(args_json)
            if not isinstance(args, dict):
                raise ValueError("--args-json must decode to an object")
        except (json.JSONDecodeError, ValueError) as e:
            err = {
                "status": "error",
                "error_code": "bad_args_json",
                "message": f"--args-json must be a valid JSON object: {e}",
            }
            _emit(err, json_out)
            raise typer.Exit(code=2)

    pm = get_pmgr().pm
    try:
        responses = pm.hook.transform_apply(
            input_path=input_path,
            transform=transform,
            args=args,
            output_path=output_path,
        )
    except Exception as e:  # noqa: BLE001 — plugin raised, surface as envelope
        err = {
            "status": "error",
            "error_code": "plugin_exception",
            "transform": transform,
            "message": f"plugin raised during transform_apply: {type(e).__name__}: {e}",
        }
        _emit(err, json_out)
        raise typer.Exit(code=1)

    envelopes = [r for r in (responses or []) if r is not None]
    if not envelopes:
        err = {
            "status": "error",
            "error_code": "unknown_transform",
            "transform": transform,
            "message": (
                f"no installed plugin claims transform={transform!r}. "
                f"Install a plugin that implements transform_apply for "
                f"this name."
            ),
        }
        _emit(err, json_out)
        raise typer.Exit(code=2)

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
            rprint(f"[green]✅ transform={payload.get('transform')} "
                   f"output={payload.get('output_path')}[/green]")
            result = payload.get("result") or {}
            if isinstance(result, dict):
                for k, v in result.items():
                    if k == "warnings" and isinstance(v, list) and not v:
                        continue
                    rprint(f"   {k}: {v}")
