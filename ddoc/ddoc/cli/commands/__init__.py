"""CLI commands module - modularized structure.

*core import surface stays light*. Heavy
deps (mlflow, etc.) live behind the ``experiment`` command group, which
is loaded **inside** ``register()`` with try/except so ``pip install
ddoc`` (core only) keeps working without those extras — only
``ddoc exp ...`` disappears from the help when its imports fail. Aligns with the
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
    # Diff Command — one-line drift verdict (the front door)
    # ========================================================================
    from .diff import diff_command
    app.command(
        name="diff",
        help="One-line drift verdict between two datasets (exit 0=OK, 1=DRIFT, 2=BLIND)",
    )(diff_command)

    # ========================================================================
    # Ingest Command (application envelope bridge)
    # ========================================================================
    app.command(name="ingest", help="Ingest application feedback-envelope JSON files into the workspace inbox")(ingest_command)
    
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

    app.add_typer(exp_app, name="exp")
    
    # ========================================================================
    # System Commands
    # ========================================================================
    plugin_app.command("list")(plugin_list_command)
    plugin_app.command("info")(plugin_info_command)
    plugin_app.command("install")(plugin_install_command)
    plugin_app.command("detectors")(plugin_detectors_command)
    app.add_typer(plugin_app, name="plugin")

    # Toy data generators for tutorials.
    from .examples import examples_app
    app.add_typer(examples_app, name="examples", help="Generate ready-to-analyze toy datasets")

    # Report rendering + export to external systems.
    from .report import report_app
    from .export import export_app
    app.add_typer(report_app, name="report", help="Render drift / EDA results as HTML / PDF / Markdown reports")
    app.add_typer(export_app, name="export", help="Ship drift / EDA results to external systems (http / file / ...)")

    # Data-source adapter (file:// fallback + plugin extension point for s3:// etc.)
    from .fetch import fetch_command
    app.command(
        name="fetch",
        help="Materialize an external data source (file/s3/gs/http) into a local directory",
    )(fetch_command)

    # REST facade (`ddoc serve`).
    from .serve import serve_command
    app.command(
        name="serve",
        help="Start a FastAPI server exposing every ddoc CLI command over HTTP",
    )(serve_command)

    # Multi-step recipes.
    from .recipe import recipe_app
    app.add_typer(recipe_app, name="recipe", help="Run a multi-step workflow described in YAML")

    # `ddoc train` invokes the `retrain_run` hookspec implemented by
    # training plugins (ddoc-plugin-yolo, ...).
    from .train import train_command
    app.command(
        name="train",
        help="Train a model via a plugin's `retrain_run` hook implementation",
    )(train_command)

    # `ddoc transform` invokes the `transform_apply` hookspec
    # implemented by transform plugins.
    from .transform import transform_command
    app.command(
        name="transform",
        help="Apply a transform via a plugin's `transform_apply` hook implementation",
    )(transform_command)

    app.command(name="vis", help="Run GUI app")(vis)


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

