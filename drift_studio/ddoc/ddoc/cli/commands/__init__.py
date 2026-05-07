"""CLI commands module - modularized structure"""
from __future__ import annotations
import typer
from typing import Optional

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

# Import v2.0 core commands
from .init import init
from .add import add
from .snapshot import snapshot_app

# Import analyze commands
from .analyze import analyze_eda_command, analyze_drift_command

# Import ingest command (Phase 2 — keti_veritas envelope bridge)
from .ingest import ingest_command

# Import system commands
from .plugin import plugin_list_command, plugin_info_command
from .vis import vis

# Import new experiment commands
from .experiment import (
    exp_train_command,
    exp_eval_command,
    exp_best_command as exp_best_command_new,
)

# Import legacy commands from legacy module
from .legacy import (
    # Dataset commands (v1.x deprecated)
    dataset_add_command,
    dataset_list_command,
    dataset_commit_command,
    dataset_status_command,
    dataset_unstage_command,
    dataset_tag_list_command,
    dataset_tag_rename_command,
    dataset_timeline_command,
    dataset_checkout_command,
    
    # Experiment commands (to be modularized later)
    exp_run_command,
    exp_list_command,
    exp_show_command,
    exp_compare_command,
    exp_status_command,
    exp_best_command,
    
    # Lineage commands (v1.x deprecated)
    lineage_show_command,
    lineage_graph_command,
    lineage_overview_command,
    lineage_impact_command,
    lineage_dependencies_command,
    lineage_dependents_command,
    
    # Deprecated v1.x commands (hidden, backwards compatibility)
    commit,
    checkout,
    log,
    status,
    alias_cmd,
    diff,
    init_old,
)


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
    # Experiment Commands
    # ========================================================================
    # New trainer-based commands
    exp_app.command("train", help="Train a model using a trainer from code/trainers/")(exp_train_command)
    exp_app.command("eval", help="Evaluate a model using an evaluator from code/trainers/")(exp_eval_command)
    exp_app.command("best", help="Find best experiment for a dataset based on a metric")(exp_best_command_new)
    
    # Legacy commands (deprecated, will be removed in future version)
    exp_app.command("run", help="[DEPRECATED] Use 'exp train' instead")(exp_run_command)
    exp_app.command("list", help="[DEPRECATED] List experiments")(exp_list_command)
    exp_app.command("show", help="[DEPRECATED] Show experiment details")(exp_show_command)
    exp_app.command("compare", help="[DEPRECATED] Compare experiments")(exp_compare_command)
    exp_app.command("status", help="[DEPRECATED] Show experiment status")(exp_status_command)
    
    app.add_typer(exp_app, name="exp")
    
    # ========================================================================
    # System Commands
    # ========================================================================
    plugin_app.command("list")(plugin_list_command)
    plugin_app.command("info")(plugin_info_command)
    app.add_typer(plugin_app, name="plugin")
    
    app.command(name="vis", help="Run GUI app")(vis)
    
    # ========================================================================
    # v1.x Legacy Commands (Hidden, for backwards compatibility)
    # Will be removed in v2.1
    # ========================================================================
    
    # Dataset commands (deprecated)
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
    
    # Lineage commands (deprecated)
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

