"""Drift analysis command.

Two input modes (Phase 3 — orchestrator pivot):

1. **Snapshot mode** (legacy / interactive): pass two snapshot IDs or
   aliases as positional arguments. The CLI resolves snapshots, loads
   the per-snapshot analysis cache, and feeds plugins.
2. **Path mode** (Phase 3 / backend orchestrator): pass
   ``--data-path-ref`` and ``--data-path-cur`` to skip snapshot/cache
   resolution entirely. Plugins receive the paths directly. Used by the
   drift_studio backend when it subprocess-invokes ddoc instead of
   importing ``run_drift`` as a library.

When ``--json`` is set the merged plugin result is printed to stdout as
a single JSON object (no rich formatting). Errors also use stdout JSON
in this mode for machine-parsable diagnostics.
"""
import json
import sys
import typer
from rich import print as rprint
from typing import Optional

from ..utils import get_pmgr, _pretty
from ddoc.core.snapshot_service import get_snapshot_service
from ddoc.core.cache_service import get_cache_service


def _emit(res: dict, json_out: bool) -> None:
    """Stdout writer — JSON envelope when --json, rich pretty otherwise."""
    if json_out:
        sys.stdout.write(json.dumps(res, ensure_ascii=False, default=str))
        sys.stdout.write("\n")
        sys.stdout.flush()
    else:
        rprint(_pretty(res))


def _emit_error(message: str, *, code: str, json_out: bool) -> None:
    if json_out:
        sys.stdout.write(json.dumps(
            {"status": "error", "error_code": code, "message": message},
            ensure_ascii=False,
        ))
        sys.stdout.write("\n")
        sys.stdout.flush()
    else:
        rprint(f"[red]❌ {message}[/red]")


def _merge_plugin_results(valid_results: list, hook_name: str) -> dict:
    """Collapse multi-plugin output into a single dict (single-modality
    case is hoisted for backward compatibility)."""
    merged: dict = {"status": "success", "modalities": {}, "summary": {}}
    pmgr = get_pmgr()
    for i, result in enumerate(valid_results):
        if not isinstance(result, dict):
            continue
        modality = result.get("modality")
        if not modality:
            try:
                hook_impls = getattr(pmgr.pm.hook, hook_name).get_hookimpls()
                if i < len(hook_impls):
                    plugin_name = pmgr.pm.get_name(hook_impls[i].plugin)
                    name = plugin_name.lower()
                    if "vision" in name:
                        modality = "image"
                    elif "text" in name:
                        modality = "text"
                    elif "timeseries" in name or "ts" in name:
                        modality = "timeseries"
                    elif "audio" in name:
                        modality = "audio"
                    else:
                        modality = f"unknown_{i}"
                else:
                    modality = f"unknown_{i}"
            except Exception:
                modality = f"unknown_{i}"
        merged["modalities"][modality] = result
        if "summary" in result:
            merged["summary"][modality] = result["summary"]
    if len(merged["modalities"]) == 1:
        only = next(iter(merged["modalities"].values()))
        return only
    return merged


def analyze_drift_command(
    baseline: Optional[str] = typer.Argument(
        None, help="Baseline snapshot ID or alias (omit when using --data-path-ref)"
    ),
    current: Optional[str] = typer.Argument(
        None, help="Current snapshot ID or alias (omit when using --data-path-cur)"
    ),
    detector: str = typer.Option("mmd", "--detector", help="Drift detector method"),
    data_path_ref: Optional[str] = typer.Option(
        None, "--data-path-ref",
        help="Skip snapshot/cache; pass baseline data path directly (orchestrator mode).",
    ),
    data_path_cur: Optional[str] = typer.Option(
        None, "--data-path-cur",
        help="Skip snapshot/cache; pass current data path directly (orchestrator mode).",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON envelope to stdout (no rich formatting).",
    ),
):
    """Detect drift between two snapshots or two data paths.

    Two input modes:
      * Snapshot: ``ddoc analyze drift v01 v02``
      * Path:     ``ddoc analyze drift --data-path-ref /a --data-path-cur /b``

    Examples:
        ddoc analyze drift baseline v05
        ddoc analyze drift v01 v02 --json
        ddoc analyze drift --data-path-ref /data/a --data-path-cur /data/b --json
    """
    # ── Mode resolution ──
    path_mode = bool(data_path_ref or data_path_cur)
    if path_mode and not (data_path_ref and data_path_cur):
        _emit_error(
            "path mode requires both --data-path-ref and --data-path-cur",
            code="path_mode_incomplete", json_out=json_out,
        )
        raise typer.Exit(code=2)
    if not path_mode and not (baseline and current):
        _emit_error(
            "snapshot mode requires both baseline and current arguments "
            "(or use --data-path-ref/--data-path-cur for path mode)",
            code="snapshot_mode_incomplete", json_out=json_out,
        )
        raise typer.Exit(code=2)

    # Path mode: skip snapshot resolution entirely.
    if path_mode:
        if not json_out:
            rprint(f"[cyan]🔍 Drift Analysis (path mode)[/cyan]")
            rprint(f"   Ref:  {data_path_ref}")
            rprint(f"   Cur:  {data_path_cur}\n")
        cfg = {
            # No cache — caller is the orchestrator, expected to manage caching outside.
            "baseline_cache": None,
            "current_cache": None,
            "baseline_metadata": None,
            "current_metadata": None,
        }
        try:
            hook_results = get_pmgr().hook.drift_detect(
                snapshot_id_ref="__path__",
                snapshot_id_cur="__path__",
                data_path_ref=data_path_ref,
                data_path_cur=data_path_cur,
                data_hash_ref="",
                data_hash_cur="",
                detector=detector,
                cfg=cfg,
                output_path=f"analysis/drift_path_{detector}",
            )
        except Exception as e:
            _emit_error(f"plugin invocation failed: {e}", code="plugin_error", json_out=json_out)
            raise typer.Exit(code=1)
        return _finish_drift(hook_results, json_out=json_out)

    # ── Snapshot mode (legacy interactive path) ──
    snapshot_service = get_snapshot_service()
    cache_service = get_cache_service()

    baseline_id = snapshot_service._resolve_version(baseline)
    current_id = snapshot_service._resolve_version(current)

    if not baseline_id:
        _emit_error(f"Snapshot '{baseline}' not found", code="snapshot_not_found", json_out=json_out)
        raise typer.Exit(code=1)
    if not current_id:
        _emit_error(f"Snapshot '{current}' not found", code="snapshot_not_found", json_out=json_out)
        raise typer.Exit(code=1)

    snap_baseline = snapshot_service._load_snapshot(baseline_id)
    snap_current = snapshot_service._load_snapshot(current_id)

    if not snap_baseline:
        _emit_error(f"Failed to load snapshot {baseline_id}", code="snapshot_load_failed", json_out=json_out)
        raise typer.Exit(code=1)
    if not snap_current:
        _emit_error(f"Failed to load snapshot {current_id}", code="snapshot_load_failed", json_out=json_out)
        raise typer.Exit(code=1)

    cache_baseline_attr = cache_service.load_analysis_cache(
        snapshot_id=baseline_id,
        data_hash=snap_baseline.data.dvc_hash,
        cache_type="attributes",
    )
    cache_current_attr = cache_service.load_analysis_cache(
        snapshot_id=current_id,
        data_hash=snap_current.data.dvc_hash,
        cache_type="attributes",
    )

    if not cache_baseline_attr:
        _emit_error(
            f"No analysis cache for {baseline_id} — run 'ddoc analyze eda {baseline_id}' first",
            code="cache_missing", json_out=json_out,
        )
        raise typer.Exit(code=1)
    if not cache_current_attr:
        _emit_error(
            f"No analysis cache for {current_id} — run 'ddoc analyze eda {current_id}' first",
            code="cache_missing", json_out=json_out,
        )
        raise typer.Exit(code=1)

    cfg = {
        "baseline_cache": cache_baseline_attr,
        "current_cache": cache_current_attr,
        "baseline_metadata": cache_service.load_file_metadata(
            snapshot_id=baseline_id, data_hash=snap_baseline.data.dvc_hash,
        ),
        "current_metadata": cache_service.load_file_metadata(
            snapshot_id=current_id, data_hash=snap_current.data.dvc_hash,
        ),
    }

    output_path = f"analysis/drift_{baseline_id}_{current_id}"

    if not json_out:
        rprint(f"[cyan]🔍 Drift Analysis[/cyan]")
        rprint(f"   Baseline: {baseline_id} ({snap_baseline.data.dvc_hash[:7]})")
        rprint(f"   Current:  {current_id} ({snap_current.data.dvc_hash[:7]})\n")

    try:
        hook_results = get_pmgr().hook.drift_detect(
            snapshot_id_ref=baseline_id,
            snapshot_id_cur=current_id,
            data_path_ref=snap_baseline.data.path,
            data_path_cur=snap_current.data.path,
            data_hash_ref=snap_baseline.data.dvc_hash,
            data_hash_cur=snap_current.data.dvc_hash,
            detector=detector,
            cfg=cfg,
            output_path=output_path,
        )
    except Exception as e:
        _emit_error(f"plugin invocation failed: {e}", code="plugin_error", json_out=json_out)
        raise typer.Exit(code=1)

    return _finish_drift(hook_results, json_out=json_out)


def _finish_drift(hook_results, *, json_out: bool) -> None:
    """Shared post-hook handling (used by both modes)."""
    if not hook_results:
        _emit_error(
            "No plugin available for drift detection. Install via: pip install ddoc-full",
            code="no_plugin", json_out=json_out,
        )
        raise typer.Exit(code=1)

    valid = [r for r in hook_results if r is not None]
    if not valid:
        _emit_error(
            "No plugin returned a valid drift result.",
            code="empty_result", json_out=json_out,
        )
        raise typer.Exit(code=1)

    res = _merge_plugin_results(valid, hook_name="drift_detect")
    _emit(res, json_out=json_out)
