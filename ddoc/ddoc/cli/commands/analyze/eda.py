"""EDA analysis command.

``ddoc analyze eda --data-path <p>`` runs the installed plugins'
``eda_run`` hooks directly on a path. Orchestrating backends can
subprocess-invoke this instead of importing ddoc as a library.

``--json`` emits the merged plugin result to stdout as a single JSON
object (no rich formatting).
"""
import typer
from rich import print as rprint
from pathlib import Path
from typing import Optional

from ..utils import get_pmgr
from .drift import _emit, _emit_error, _merge_plugin_results, emit_progress, _SilencePluginIO


def analyze_eda_command(
    data_path: Optional[str] = typer.Option(
        None, "--data-path",
        help="Data path to analyze.",
    ),
    invalidate_cache: bool = typer.Option(False, "--invalidate-cache", help="Invalidate existing cache before analysis"),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON envelope to stdout (no rich formatting).",
    ),
    ndjson_progress: bool = typer.Option(
        False, "--ndjson-progress",
        help="Emit NDJSON progress lines on stderr (orchestrator streaming).",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Silence all plugin stdout/stderr during hook invocation. CLI's own NDJSON progress (if --ndjson-progress) and final --json envelope still emit.",
    ),
):
    """
    Run EDA analysis on a data path.

    Examples:
        ddoc analyze eda --data-path /data/x
        ddoc analyze eda --data-path /data/x --json
    """
    if not data_path:
        _emit_error(
            "--data-path is required",
            code="path_mode_incomplete", json_out=json_out,
        )
        raise typer.Exit(code=2)

    emit_progress(0.05, "start", "eda path mode init", enabled=ndjson_progress)
    if not json_out:
        rprint(f"[cyan]📊 EDA Analysis[/cyan]")
        rprint(f"   Path: {data_path}\n")
    emit_progress(0.2, "plugin_call", "invoking eda_run hook",
                  enabled=ndjson_progress)
    try:
        with _SilencePluginIO(json_out=json_out, quiet=quiet):
            hook_results = get_pmgr().hook.eda_run(
                snapshot_id="__path__",
                data_path=data_path,
                data_hash="",
                output_path=f"analysis/path_{Path(data_path).name}",
                invalidate_cache=invalidate_cache,
            )
    except Exception as e:
        _emit_error(f"plugin invocation failed: {e}", code="plugin_error", json_out=json_out)
        raise typer.Exit(code=1)
    emit_progress(0.9, "merge", "merging plugin results",
                  enabled=ndjson_progress)
    result = _finish_eda(hook_results, json_out=json_out)
    emit_progress(1.0, "complete", "done", enabled=ndjson_progress)
    return result


def _finish_eda(hook_results, *, json_out: bool, return_dict: bool = False):
    """Shared post-hook handling. Returns the merged dict if ``return_dict``."""
    if not hook_results:
        _emit_error(
            "No plugin available for EDA analysis. Install via: pip install ddoc-full",
            code="no_plugin", json_out=json_out,
        )
        if return_dict:
            return None
        raise typer.Exit(code=1)

    valid = [r for r in hook_results if r is not None]
    if not valid:
        _emit_error(
            "No plugin returned a valid result.",
            code="empty_result", json_out=json_out,
        )
        if return_dict:
            return None
        raise typer.Exit(code=1)

    res = _merge_plugin_results(valid, hook_name="eda_run")
    _emit(res, json_out=json_out)
    return res if return_dict else None
