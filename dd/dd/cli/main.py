from __future__ import annotations
import typer
from dd.cli.commands import app as dd_app
from dd.core.plugins import get_plugin_manager

app = typer.Typer(help="dd: Data drift & lifecycle CLI")

@app.callback()
def _bootstrap():
    # Creating the plugin manager ensures builtins + entry points are loaded.
    get_plugin_manager()

app.add_typer(dd_app, name="")

if __name__ == "__main__":
    app()