"""``ddoc ingest`` — read keti_veritas-style envelope JSON into the workspace.

This is the receiving side of the keti_veritas → ddoc bridge described in
`_specs/ddoc_orchestrator_pattern.md` (Phase 2). The CLI is intentionally
thin — all parsing / writing logic lives in :mod:`ddoc.core.ingest_service`.

Phase 4 adds a ``--dvc-pull`` flag that runs ``dvc pull`` against the
source directory before scanning, so air-gapped sites can drop their
envelopes into a DVC remote and let the receiving site pull them in one
command.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table
from rich.console import Console

from ddoc.core.ingest_service import ingest_directory
from ddoc.core.logging import get_logger

logger = get_logger(__name__)
console = Console()


def ingest_command(
    from_dir: Path = typer.Option(
        ...,
        "--from-dir",
        "-f",
        help="Directory containing envelope JSON files (e.g. keti_veritas DD_EXPORT_DIR).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    site_id: Optional[str] = typer.Option(
        None,
        "--site-id",
        "-s",
        help="Override site identifier. Defaults to the envelope's source.app_id.",
    ),
    workspace: Path = typer.Option(
        Path.cwd(),
        "--workspace",
        "-w",
        help="ddoc workspace root (where .ddoc/inbox/ lives).",
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    inbox: Optional[Path] = typer.Option(
        None,
        "--inbox",
        help="Override inbox root (default: <workspace>/.ddoc/inbox).",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    mode: str = typer.Option(
        "move",
        "--mode",
        help="What to do with consumed source files: move (to .processed/) or delete.",
    ),
    parquet: bool = typer.Option(
        False,
        "--parquet",
        help="Write parquet alongside CSV (requires pyarrow).",
    ),
    dvc_pull: bool = typer.Option(
        False,
        "--dvc-pull",
        help="Run 'dvc pull <from-dir>' before scanning (Phase 4 — pulls "
             "envelope files from the configured DVC remote first).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON outcome to stdout instead of a table.",
    ),
):
    """Ingest envelope JSON files (protocol 1.1) from a directory.

    The directory typically points at a keti_veritas instance's
    ``DD_EXPORT_DIR`` — directly, via shared NAS, or after ``dvc pull``.
    Each envelope contributes its ``decision_batch`` rows to a CSV
    aggregate file under ``<workspace>/.ddoc/inbox/<site_id>/decisions/``,
    and any ``drift_report`` payload as a sidecar JSON. Source files are
    moved to ``.processed/`` (or deleted with ``--mode delete``).

    Examples:
        ddoc ingest --from-dir /tmp/keti_export
        ddoc ingest -f /mnt/nas/site_a/audit -s site_a -w ~/ddoc-ws
        ddoc ingest -f export/ --json   # for scripts
    """
    if mode not in {"move", "delete"}:
        rprint(f"[red]error:[/red] --mode must be 'move' or 'delete', got {mode!r}")
        raise typer.Exit(code=2)

    # Phase 4 — opportunistic DVC pull. If `dvc` is on PATH and the cwd
    # has a `.dvc/` directory, pull the target dir; otherwise warn and
    # carry on (the local from_dir might still have content).
    if dvc_pull:
        dvc_bin = shutil.which("dvc")
        if not dvc_bin:
            rprint("[yellow]warn:[/yellow] --dvc-pull requested but 'dvc' not on PATH; skipping")
        else:
            try:
                # Pull just this target dir if possible; fall back to a full pull.
                proc = subprocess.run(
                    [dvc_bin, "pull", str(from_dir)],
                    capture_output=True, text=True, timeout=300,
                )
                if proc.returncode != 0:
                    rprint(f"[yellow]warn:[/yellow] dvc pull returned {proc.returncode}; continuing")
                    if proc.stderr:
                        rprint(f"  stderr: {proc.stderr.strip()[:300]}")
            except Exception as e:
                rprint(f"[yellow]warn:[/yellow] dvc pull failed: {e}; continuing")

    try:
        outcome = ingest_directory(
            from_dir=from_dir,
            workspace_root=workspace,
            site_id=site_id,
            inbox_root=inbox,
            mode=mode,
            use_parquet=parquet,
        )
    except (FileNotFoundError, ValueError) as e:
        if json_out:
            print(json.dumps({"error_type": type(e).__name__, "message": str(e)}))
        else:
            rprint(f"[red]ingest failed:[/red] {e}")
        raise typer.Exit(code=2)

    if json_out:
        print(json.dumps(outcome.to_dict(), ensure_ascii=False, indent=2, default=str))
        return

    # Pretty table output
    table = Table(title=f"ddoc ingest — site_id={outcome.site_id}", show_header=False)
    table.add_column("metric", style="cyan")
    table.add_column("value")
    table.add_row("inbox", outcome.inbox_dir)
    table.add_row("files seen", str(outcome.files_seen))
    table.add_row("files processed", str(outcome.files_processed))
    table.add_row("files skipped", str(len(outcome.files_skipped)))
    table.add_row("decision rows", str(outcome.decision_rows))
    table.add_row("drift reports", str(outcome.drift_reports))
    if outcome.decisions_path:
        table.add_row("decisions csv", outcome.decisions_path)
    if outcome.manifest_path:
        table.add_row("manifest", outcome.manifest_path)
    console.print(table)

    if outcome.files_skipped:
        rprint("\n[yellow]skipped files:[/yellow]")
        for s in outcome.files_skipped[:10]:
            rprint(f"  - {s.get('file', '?')}: {s.get('reason', '')}")
        if len(outcome.files_skipped) > 10:
            rprint(f"  ... and {len(outcome.files_skipped) - 10} more")
