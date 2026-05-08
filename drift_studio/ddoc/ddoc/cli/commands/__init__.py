"""CLI commands module - modularized structure.

Round-2 (2026-05-07) — *core import surface stays light*. Heavy
deps (mlflow, ultralytics, etc.) live behind the ``experiment`` and
``legacy`` command groups. Those are loaded **inside** ``register()``
with try/except so ``pip install ddoc`` (core only) keeps working
without those extras — only ``ddoc exp ...`` / ``ddoc dataset ...``
disappear from the help when their imports fail. Aligns with the
PyPI distribution intent (lightweight core, opt-in extras).
"""
from __future__ import annotations
import logging
import typer
from typing import Optional

logger = logging.getLogger(__name__)

# Create Typer sub-apps
analyze_app = typer.Typer(help="Data analysis commands (eda, drift)")
exp_app = typer.Typer(help="Experiment management commands (run, list, show, compare, status)")
plugin_app = typer.Typer(help="Plugin management commands (list, info)")

# Legacy apps (v1.x, will be removed in v2.1)
dataset_app = typer.Typer(help="[DEPRECATED] Dataset management commands", hidden=True)
tag_app = typer.Typer(help="[DEPRECATED] Dataset version tag management", hidden=True, invoke_without_command=False)
lineage_app = typer.Typer(help="[DEPRECATED] Lineage tracking commands", hidden=True)

# Register tag_app under dataset_app
dataset_app.add_typer(tag_app, name="tag")

# ── Core commands — light deps, always available ──────────────────────
from .init import init
from .add import add
from .snapshot import snapshot_app
from .analyze import analyze_eda_command, analyze_drift_command
from .ingest import ingest_command
from .plugin import plugin_list_command, plugin_info_command, plugin_install_command, plugin_detectors_command
from .vis import vis


def register(app: typer.Typer) -> None:
    """
    Register all CLI commands to the main Typer app.
    
    This is the central registration point called from main.py.
    """
    # ========================================================================
    # v2.0 Core Commands (Top-level, most important)
    # ========================================================================
    app.command(name="init", help="Initialize a new ddoc workspace with scaffolding")(init)
    app.command(name="add", help="Add files to the ddoc workspace (data/code/notebook)")(add)
    app.add_typer(snapshot_app, name="snapshot", help="Snapshot management - create, list, inspect, and checkout snapshots")
    
    # ========================================================================
    # Analysis Commands
    # ========================================================================
    analyze_app.command("eda")(analyze_eda_command)
    analyze_app.command("drift")(analyze_drift_command)
    app.add_typer(analyze_app, name="analyze")

    # ========================================================================
    # Ingest Command (keti_veritas envelope bridge — Phase 2)
    # ========================================================================
    app.command(name="ingest", help="Ingest keti_veritas-style envelope JSON files into the workspace inbox")(ingest_command)
    
    # ========================================================================
    # Experiment Commands (heavy deps — mlflow et al; lazy)
    # ========================================================================
    try:
        from .experiment import (
            exp_train_command,
            exp_eval_command,
            exp_best_command as exp_best_command_new,
        )
        exp_app.command("train", help="Train a model using a trainer from code/trainers/")(exp_train_command)
        exp_app.command("eval", help="Evaluate a model using an evaluator from code/trainers/")(exp_eval_command)
        exp_app.command("best", help="Find best experiment for a dataset based on a metric")(exp_best_command_new)
    except ImportError as e:
        logger.warning(
            "[ddoc] 'exp train/eval/best' unavailable — missing dep: %s. "
            "Install with: pip install ddoc[exp]",
            getattr(e, "name", e),
        )

    # Legacy exp commands also depend on mlflow → bundle in same lazy block.
    try:
        from .legacy import (
            exp_run_command,
            exp_list_command,
            exp_show_command,
            exp_compare_command,
            exp_status_command,
        )
        exp_app.command("run", help="[DEPRECATED] Use 'exp train' instead")(exp_run_command)
        exp_app.command("list", help="[DEPRECATED] List experiments")(exp_list_command)
        exp_app.command("show", help="[DEPRECATED] Show experiment details")(exp_show_command)
        exp_app.command("compare", help="[DEPRECATED] Compare experiments")(exp_compare_command)
        exp_app.command("status", help="[DEPRECATED] Show experiment status")(exp_status_command)
    except ImportError as e:
        logger.debug(
            "[ddoc] legacy exp commands unavailable — missing dep: %s",
            getattr(e, "name", e),
        )

    app.add_typer(exp_app, name="exp")
    
    # ========================================================================
    # System Commands
    # ========================================================================
    plugin_app.command("list")(plugin_list_command)
    plugin_app.command("info")(plugin_info_command)
    plugin_app.command("install")(plugin_install_command)
    plugin_app.command("detectors")(plugin_detectors_command)
    app.add_typer(plugin_app, name="plugin")

    # Round 11 (Track A) — toy data generators for tutorials.
    from .examples import examples_app
    app.add_typer(examples_app, name="examples", help="Generate ready-to-analyze toy datasets")

    # Round 11 (Track C) — report rendering + export to external systems.
    from .report import report_app
    from .export import export_app
    app.add_typer(report_app, name="report", help="Render drift / EDA results as HTML / PDF / Markdown reports")
    app.add_typer(export_app, name="export", help="Ship drift / EDA results to external systems (keti_veritas / file / ...)")

    # Round 13 — data-source adapter (file:// fallback + plugin extension point for s3:// etc.)
    from .fetch import fetch_command
    app.command(
        name="fetch",
        help="Materialize an external data source (file/s3/gs/http) into a local directory",
    )(fetch_command)

    app.command(name="vis", help="Run GUI app")(vis)
    
    # ========================================================================
    # v1.x Legacy Commands (Hidden, for backwards compatibility)
    # Heavy deps (mlflow, ultralytics, ...) — lazy try/except. Some of
    # these legacy modules import the same heavy chain as ``experiment``,
    # so silently skip if unavailable. Will be removed in v2.1.
    # ========================================================================
    try:
        from .legacy import (
            dataset_add_command,
            dataset_list_command,
            dataset_commit_command,
            dataset_status_command,
            dataset_unstage_command,
            dataset_tag_list_command,
            dataset_tag_rename_command,
            dataset_timeline_command,
            dataset_checkout_command,
            lineage_show_command,
            lineage_graph_command,
            lineage_overview_command,
            lineage_impact_command,
            lineage_dependencies_command,
            lineage_dependents_command,
            commit,
            checkout,
            log,
            status,
            alias_cmd,
            diff,
        )

        # Dataset commands
        dataset_app.command("add")(dataset_add_command)
        dataset_app.command("list")(dataset_list_command)
        dataset_app.command("commit")(dataset_commit_command)
        dataset_app.command("status")(dataset_status_command)
        dataset_app.command("unstage")(dataset_unstage_command)
        dataset_app.command("timeline")(dataset_timeline_command)
        dataset_app.command("checkout")(dataset_checkout_command)
        tag_app.command("list")(dataset_tag_list_command)
        tag_app.command("rename")(dataset_tag_rename_command)
        app.add_typer(dataset_app, name="dataset")

        # Lineage commands
        lineage_app.command("show")(lineage_show_command)
        lineage_app.command("graph")(lineage_graph_command)
        lineage_app.command("overview")(lineage_overview_command)
        lineage_app.command("impact")(lineage_impact_command)
        lineage_app.command("dependencies")(lineage_dependencies_command)
        lineage_app.command("dependents")(lineage_dependents_command)
        app.add_typer(lineage_app, name="lineage")

        # Top-level deprecated commands (hidden)
        app.command(name="commit", hidden=True, deprecated=True)(commit)
        app.command(name="checkout", hidden=True, deprecated=True)(checkout)
        app.command(name="log", hidden=True, deprecated=True)(log)
        app.command(name="status", hidden=True, deprecated=True)(status)
        app.command(name="alias", hidden=True, deprecated=True)(alias_cmd)
        app.command(name="diff", hidden=True, deprecated=True)(diff)
    except ImportError as e:
        logger.debug(
            "[ddoc] legacy commands unavailable — missing dep: %s",
            getattr(e, "name", e),
        )


# Export main components
__all__ = [
    'register',
    'init',
    'add',
    'snapshot',
    'analyze_app',
    'exp_app',
    'plugin_app',
    'vis',
]

