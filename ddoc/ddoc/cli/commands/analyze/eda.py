"""EDA analysis command.

Three input modes (Phase 3 — orchestrator pivot):

1. **Workspace** (default): no positional args, no ``--data-path`` → analyses
   the current workspace.
2. **Snapshot**: ``ddoc analyze eda <snapshot>`` → loads snapshot's data hash.
3. **Path**: ``ddoc analyze eda --data-path <p>`` → bypasses snapshot/cache,
   runs plugin directly on a path. Used by drift_studio backend orchestrator.

``--json`` emits the merged plugin result to stdout as a single JSON
object (no rich formatting, no interactive ``input()``).
"""
import json
import sys
import typer
from rich import print as rprint
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..utils import get_pmgr, _pretty
from ddoc.core.snapshot_service import get_snapshot_service
from ddoc.core.cache_service import get_cache_service
from .drift import _emit, _emit_error, _merge_plugin_results, emit_progress, _SilencePluginIO


def analyze_eda_command(
    snapshot: Optional[str] = typer.Argument(None, help="Snapshot ID or alias (default: current workspace; ignore when --data-path)"),
    invalidate_cache: bool = typer.Option(False, "--invalidate-cache", help="Invalidate existing cache before analysis"),
    save_snapshot: bool = typer.Option(False, "--save-snapshot", help="Save workspace as permanent snapshot after analysis (interactive — incompatible with --json)"),
    strict_hash: bool = typer.Option(
        False, "--strict-hash",
        help="Refuse to run when the snapshot's data_hash does not match the workspace (forces the user to ``ddoc snapshot checkout`` first). Default: warn-only with provenance-correct cache routing.",
    ),
    data_path: Optional[str] = typer.Option(
        None, "--data-path",
        help="Skip snapshot/workspace; pass data path directly (orchestrator mode).",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON envelope to stdout (no rich formatting, no interactive prompts).",
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
    Run EDA analysis on a snapshot, current workspace, or arbitrary data path.

    Examples:
        ddoc analyze eda                              # current workspace
        ddoc analyze eda --save-snapshot              # workspace + permanent snapshot
        ddoc analyze eda baseline                     # baseline snapshot
        ddoc analyze eda v01                          # v01 snapshot
        ddoc analyze eda --data-path /data/x --json   # path mode, machine-readable
    """
    # ── Path mode (orchestrator) ──
    if data_path:
        if save_snapshot:
            _emit_error(
                "--save-snapshot is not compatible with --data-path (path mode is stateless)",
                code="incompatible_options", json_out=json_out,
            )
            raise typer.Exit(code=2)
        emit_progress(0.05, "start", "eda path mode init", enabled=ndjson_progress)
        if not json_out:
            rprint(f"[cyan]📊 EDA Analysis (path mode)[/cyan]")
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

    # JSON mode silences noisy progress logging (stdout would otherwise
    # carry both rich-formatted lines and the final JSON envelope, breaking
    # parsers). Errors and the final result still go through the dedicated
    # ``_emit*`` helpers.
    _log = (lambda *a, **k: None) if json_out else rprint

    snapshot_service = get_snapshot_service()
    cache_service = get_cache_service()

    # Resolve snapshot or use workspace state
    if snapshot:
        snapshot_id = snapshot_service._resolve_version(snapshot)
        if not snapshot_id:
            _log(f"[red]❌ Snapshot '{snapshot}' not found[/red]")
            return
        
        snap = snapshot_service._load_snapshot(snapshot_id)
        if not snap:
            _log(f"[red]❌ Failed to load snapshot {snapshot_id}[/red]")
            return
        
        # Get snapshot data info
        snapshot_data_hash = snap.data.dvc_hash
        # Snapshot data path is always relative to project root: "data/"
        # Actual path is project_root / "data/"
        snapshot_data_path = str(snapshot_service.project_root / snap.data.path)
        
        # Check current workspace data hash
        current_data_hash = snapshot_service._get_dvc_data_hash() or "unknown"
        
        # Always use current workspace data path for analysis
        # (Analysis operates on actual files in workspace)
        data_path = "data/"  # Relative path from project root

        hashes_match = (
            snapshot_data_hash == current_data_hash
            or current_data_hash == "unknown"
        )

        # Round-7 (2026-05-08) — provenance-correct cache routing.
        # When the workspace data does NOT match the requested
        # snapshot, we used to cache the analysis result under the
        # *snapshot's* hash anyway, which silently corrupted drift
        # comparisons against that snapshot. Now we cache under the
        # *workspace's actual* hash (whatever was analyzed). Drift
        # against the original snapshot data correctly returns
        # cache_missing — which is the truthful outcome — and the user
        # is told to ``ddoc snapshot checkout`` first.
        if hashes_match:
            data_hash = snapshot_data_hash
        else:
            if strict_hash:
                _emit_error(
                    f"--strict-hash: snapshot {snapshot_id} expects {snapshot_data_hash[:8]} "
                    f"but workspace has {current_data_hash[:8]}. "
                    f"Run 'ddoc snapshot checkout {snapshot_id}' first.",
                    code="hash_mismatch", json_out=json_out,
                )
                raise typer.Exit(code=2)
            _log(f"[red]⚠️  HASH MISMATCH — snapshot {snapshot_id} expects {snapshot_data_hash[:8]} but workspace currently has {current_data_hash[:8]}[/red]")
            _log(f"[red]   EDA will analyze the workspace data and cache the result under the WORKSPACE hash ({current_data_hash[:8]}), not the snapshot's hash.[/red]")
            _log(f"[red]   Drift against {snapshot_id} will report cache_missing until you run:  ddoc snapshot checkout {snapshot_id}  and re-run EDA.[/red]")
            _log(f"[red]   Pass --strict-hash to make this a hard error instead of a warning.[/red]\n")
            data_hash = current_data_hash
        
        is_workspace = False
    else:
        # Use workspace state
        # Ensure DVC tracking is up to date before analysis
        # This guarantees consistent hash between EDA and snapshot
        data_changed = snapshot_service._has_data_changes()
        if data_changed:
            _log("[cyan]📦 Updating DVC tracking to ensure consistent hash...[/cyan]")
            import subprocess
            result = subprocess.run(
                ["dvc", "add", "data/"],
                cwd=snapshot_service.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                _log(f"[yellow]⚠️  DVC add failed: {result.stderr}[/yellow]")
                _log("[yellow]   Analysis will proceed but hash may be inconsistent.[/yellow]")
            else:
                _log("[green]✅ DVC tracking updated[/green]")
        
        workspace_state = snapshot_service.get_workspace_state()
        snapshot_id = workspace_state["snapshot_id"]
        data_path = workspace_state["data"]["path"]
        data_hash = workspace_state["data"]["dvc_hash"]
        is_workspace = True
        
        _log(f"[cyan]📊 Current workspace data_hash: {data_hash[:8]}...[/cyan]")
        
        if data_hash == "unknown":
            _log("[yellow]⚠️  No DVC tracking found. Run 'ddoc add --data' first.[/yellow]")
            _log("[yellow]   Analysis will proceed but cache may not be reusable.[/yellow]")
        else:
            # Sync workspace cache with current data hash for incremental analysis
            sync_result = cache_service.sync_workspace_cache(data_hash)
            if sync_result.get("synced"):
                _log(f"[cyan]🔄 Synced cache: {sync_result['old_hash']} → {sync_result['new_hash']}[/cyan]")
                _log(f"[cyan]   Cache types: {', '.join(sync_result['cache_types'])}[/cyan]")
    
    # Check cache
    if not invalidate_cache:
        # Try to find cache by data hash
        cache = cache_service.load_analysis_cache(data_hash=data_hash, cache_type="summary")
        if cache:
            _log(f"[cyan]📋 Found existing cache for data hash {data_hash[:8]}...[/cyan]")
            # Check if there are other snapshots with same data hash
            snapshots_with_same_data = cache_service.find_snapshots_by_data_hash(data_hash)
            if len(snapshots_with_same_data) > 0:
                _log(f"[cyan]   Shared with snapshots: {', '.join(snapshots_with_same_data)}[/cyan]")
    
    # Output path
    if is_workspace:
        output_path = "analysis/workspace"
        _log(f"[cyan]📊 Analyzing current workspace state[/cyan]")
        if not save_snapshot:
            _log(f"[yellow]💡 Tip: Use --save-snapshot to save this state as a permanent snapshot[/yellow]\n")
    else:
        output_path = f"analysis/{snapshot_id}"
        _log(f"[cyan]📊 Analyzing snapshot: {snapshot_id}[/cyan]\n")
    
    # Call plugins (multi-modal support: collect all non-None results)
    emit_progress(0.2, "plugin_call", "invoking eda_run hook",
                  enabled=ndjson_progress)
    try:
        with _SilencePluginIO(json_out=json_out, quiet=quiet):
            hook_results = get_pmgr().hook.eda_run(
                snapshot_id=snapshot_id,
                data_path=data_path,
                data_hash=data_hash,
                output_path=output_path,
                invalidate_cache=invalidate_cache,
            )
    except Exception as e:
        _emit_error(f"plugin invocation failed: {e}", code="plugin_error", json_out=json_out)
        raise typer.Exit(code=1)

    emit_progress(0.9, "merge", "merging plugin results",
                  enabled=ndjson_progress)
    res = _finish_eda(hook_results, json_out=json_out, return_dict=True)
    if res is None:
        return  # error already emitted

    # Verify hash consistency after analysis (for workspace analysis only)
    if is_workspace and isinstance(res, dict) and res.get("status") == "success":
        final_data_hash = snapshot_service._get_dvc_data_hash() or "unknown"
        if final_data_hash != data_hash and data_hash != "unknown":
            if not json_out:
                _log(f"[yellow]⚠️  Data hash changed during analysis![/yellow]")
                rprint(f"   Before: {data_hash[:8]}...")
                rprint(f"   After:  {final_data_hash[:8]}...")
                _log(f"[yellow]   Data may have been modified during analysis.[/yellow]")
                _log(f"[yellow]   Cache was saved with old hash. Consider re-running analysis.[/yellow]")
            data_hash = final_data_hash

    # Save snapshot if requested (interactive — disabled in JSON mode)
    if is_workspace and save_snapshot and isinstance(res, dict) and res.get("status") == "success":
        if json_out:
            # JSON mode is non-interactive; surface a warning and skip.
            rprint(
                "[yellow]--save-snapshot ignored in --json mode (no interactive prompt available).[/yellow]",
                file=sys.stderr,
            )
        else:
            message = input("\nEnter snapshot message (or press Enter for default): ").strip()
            if not message:
                message = f"EDA analysis: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            alias_input = input("Enter snapshot alias (optional, press Enter to skip): ").strip()
            alias = alias_input if alias_input else None
            result = snapshot_service.create_snapshot(
                message=message, alias=alias, auto_commit=True,
            )
            if result["success"]:
                new_snapshot_id = result["snapshot_id"]
                cache_service._save_snapshot_mapping(new_snapshot_id, data_hash)
                _log(f"[green]✅ Saved as snapshot: {new_snapshot_id}[/green]")
                if alias:
                    _log(f"[green]   Alias: {alias}[/green]")


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
