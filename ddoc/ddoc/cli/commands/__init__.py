"""CLI commands module - modularized structure.

*core import surface stays light*. Heavy
analysis deps live in plugins, which are installed separately, so
``pip install ddoc`` stays a lightweight core.
"""
from __future__ import annotations
import typer
from typing import Optional

# Create Typer sub-apps
analyze_app = typer.Typer(help="Data analysis commands (eda, drift)")
plugin_app = typer.Typer(help="Plugin management commands (list, info)")

# ── Core commands — light deps, always available ──────────────────────
from .analyze import analyze_eda_command, analyze_drift_command
from .plugin import plugin_list_command, plugin_info_command, plugin_install_command, plugin_detectors_command


def register(app: typer.Typer) -> None:
    """
    Register all CLI commands to the main Typer app.
    
    This is the central registration point called from main.py.
    """
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

    # `ddoc transform` invokes the `transform_apply` hookspec
    # implemented by transform plugins.
    from .transform import transform_command
    app.command(
        name="transform",
        help="Apply a transform via a plugin's `transform_apply` hook implementation",
    )(transform_command)



# Export main components
__all__ = [
    'register',
    'analyze_app',
    'plugin_app',
]

