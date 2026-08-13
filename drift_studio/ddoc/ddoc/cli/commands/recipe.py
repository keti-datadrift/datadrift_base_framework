"""``ddoc recipe`` — chain multiple ddoc steps via a YAML file.

Round 16 — turns the Round 15 GUI's one-shot dance (fetch → analyze →
report → export through 4 separate submits) into a single declarative
file. Useful for CI, scheduled jobs, and "I always run these 4 things
together" workflows.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from ddoc.core.recipe import (
    Recipe, RecipeError, _STEP_KINDS, execute_recipe,
)


recipe_app = typer.Typer(help="Run a multi-step ddoc workflow defined in YAML.")


@recipe_app.command("validate")
def recipe_validate(
    path: Path = typer.Argument(..., help="Recipe YAML file."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable envelope."),
):
    """Parse + validate a recipe without running any steps."""
    try:
        recipe = Recipe.load(path)
    except RecipeError as e:
        _emit_error(e, json_out=json_out)
        raise typer.Exit(code=2)
    issues = recipe.validate()
    body = {
        "status": "ok" if not issues else "error",
        "recipe": recipe.name or path.name,
        "step_count": len(recipe.steps),
        "issues": issues,
    }
    if json_out:
        sys.stdout.write(json.dumps(body, ensure_ascii=False, default=str) + "\n")
    else:
        if issues:
            rprint(f"[red]❌ {len(issues)} issue(s):[/red]")
            for i in issues:
                rprint(f"  • {i}")
        else:
            rprint(f"[green]✅ {recipe.name or path.name} — {len(recipe.steps)} step(s) OK[/green]")
    if issues:
        raise typer.Exit(code=2)


@recipe_app.command("run")
def recipe_run(
    path: Path = typer.Argument(..., help="Recipe YAML file."),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Print the argv each step would run, don't actually execute.",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Machine-readable envelope to stdout. Otherwise pretty progress.",
    ),
):
    """Execute every step in the recipe in order.

    Stops at the first failing step and surfaces the error envelope.
    Each step's ``${steps.<id>.output}`` and ``${steps.<id>.json...}``
    are available to subsequent steps via the substitution machinery.
    """
    try:
        recipe = Recipe.load(path)
    except RecipeError as e:
        _emit_error(e, json_out=json_out)
        raise typer.Exit(code=2)

    def _on_step(sr) -> None:
        if json_out:
            return
        if sr.skipped:
            rprint(f"[dim]→ {sr.id} ({sr.run}) — would run: ddoc {' '.join(sr.argv)}[/dim]")
        else:
            rprint(f"[cyan]✓ {sr.id} ({sr.run})[/cyan] [dim]({sr.elapsed_ms} ms)[/dim]")

    try:
        result = execute_recipe(recipe, dry_run=dry_run, on_step=_on_step)
    except RecipeError as e:
        _emit_error(e, json_out=json_out)
        raise typer.Exit(code=2)

    if json_out:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    else:
        if result["status"] == "error":
            rprint(f"[red]❌ recipe failed at step {result.get('failed_step')!r}: "
                   f"{result.get('error', {}).get('message')}[/red]")
        else:
            rprint(
                f"[green]✅ recipe '{result.get('recipe') or path.name}' "
                f"finished — {len(result['steps'])} step(s)[/green]"
            )

    if result["status"] != "success":
        raise typer.Exit(code=1)


@recipe_app.command("kinds")
def recipe_kinds():
    """List the step kinds (`run` values) recipes can use."""
    rprint("[bold cyan]🍳 supported recipe step kinds[/bold cyan]\n")
    for kind, spec in _STEP_KINDS.items():
        argv = " ".join(spec["argv"])
        rprint(f"  [bold]{kind}[/bold]  → ddoc {argv}")
        opts = list(spec.get("options", {}).keys())
        if opts:
            rprint(f"     with: {', '.join(opts)}")


def _emit_error(e: RecipeError, *, json_out: bool) -> None:
    if json_out:
        sys.stdout.write(json.dumps(e.to_dict(), ensure_ascii=False, default=str) + "\n")
    else:
        rprint(f"[red]❌ {e}[/red]")
