"""``ddoc examples`` — generate ready-to-analyze toy datasets.

Round 11 (Track A) — exposes the ``tests/fixtures/factories.py``
toy-data generators as a user-facing CLI so people learning ddoc can
get a first drift result in 5 minutes without producing real data:

    ddoc examples list
    ddoc examples generate timeseries --out /tmp/ts --scenario shifted
    ddoc analyze drift --data-path-ref /tmp/ts/ref --data-path-cur /tmp/ts/cur --json

The factories live in ``tests/fixtures/`` because they're also pytest
fixtures' source. We add ``tests/`` to ``sys.path`` once at import
time; this is fine for a developer-tooling CLI and avoids duplicating
the generators inside ``ddoc/``.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint


def _import_factories():
    """Resolve and import ``tests.fixtures.factories``. We try the
    repo-relative path first (editable install / monorepo dev) and
    raise a helpful error if the toy data generators aren't reachable.
    """
    # Walk up from this file to the repo root (drift_studio/ddoc/),
    # which contains tests/.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "tests" / "fixtures" / "factories.py"
        if candidate.exists():
            sys.path.insert(0, str(parent / "tests"))
            from fixtures import factories  # type: ignore[import-not-found]
            return factories
    raise ImportError(
        "could not locate tests/fixtures/factories.py — install ddoc in editable mode "
        "(`pip install -e .`) from the repo so the toy-data generators are reachable."
    )


examples_app = typer.Typer(help="Generate ready-to-analyze toy datasets for tutorials and quick smoke tests.")


@examples_app.command("list")
def list_examples():
    """List the supported (modality, scenario) combinations."""
    factories = _import_factories()
    rprint("[bold cyan]📚 ddoc toy datasets[/bold cyan]\n")
    rprint("Modalities:")
    for name in factories.PAIR_BUILDERS:
        rprint(f"  • [bold]{name}[/bold]")
    rprint("\nScenarios:")
    for s in factories.SUPPORTED_SCENARIOS:
        if s == "shifted":
            rprint(f"  • [bold]{s}[/bold]    — ref vs cur with a clear distribution shift (drift ≫ 0)")
        else:
            rprint(f"  • [bold]{s}[/bold]  — ref and cur identical (drift ≈ 0; sanity check)")
    rprint(
        "\n[dim]💡 Try: ddoc examples generate timeseries --out /tmp/ex --scenario shifted &&"
        " ddoc analyze drift --data-path-ref /tmp/ex/ref --data-path-cur /tmp/ex/cur --json[/dim]"
    )


@examples_app.command("generate")
def generate_example(
    modality: str = typer.Argument(
        ..., help="One of: timeseries, audio, text, vision (run `ddoc examples list` to see)."
    ),
    out: Path = typer.Option(
        ..., "--out", "-o",
        help="Output directory. Will contain `ref/` and `cur/` subdirectories.",
    ),
    scenario: str = typer.Option(
        "shifted", "--scenario", "-s",
        help="`shifted` (default) for a drift scenario, or `identical` for a sanity-check pair.",
    ),
):
    """Generate a (ref, cur) toy dataset pair for the given modality.

    Example:
        ddoc examples generate audio --out /tmp/audio --scenario shifted
        ddoc analyze drift --data-path-ref /tmp/audio/ref --data-path-cur /tmp/audio/cur --json
    """
    factories = _import_factories()
    if modality not in factories.PAIR_BUILDERS:
        rprint(f"[red]❌ unknown modality: {modality!r}[/red]")
        rprint(f"   supported: {', '.join(factories.PAIR_BUILDERS.keys())}")
        raise typer.Exit(code=2)
    if scenario not in factories.SUPPORTED_SCENARIOS:
        rprint(f"[red]❌ unknown scenario: {scenario!r}[/red]")
        rprint(f"   supported: {', '.join(factories.SUPPORTED_SCENARIOS)}")
        raise typer.Exit(code=2)

    out.mkdir(parents=True, exist_ok=True)
    rprint(f"[cyan]📦 Generating {modality} ({scenario}) under {out}...[/cyan]")

    builder = factories.PAIR_BUILDERS[modality]
    try:
        ref_dir, cur_dir = builder(out, scenario=scenario)
    except ImportError as e:
        rprint(f"[red]❌ Missing dependency for {modality}: {e}[/red]")
        rprint(f"[yellow]   Install with: pip install ddoc-plugin-{modality}[/yellow]")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]❌ Failed to generate {modality}: {e}[/red]")
        raise typer.Exit(code=1)

    rprint(f"[green]✅ Wrote ref → {ref_dir}[/green]")
    rprint(f"[green]✅ Wrote cur → {cur_dir}[/green]")
    rprint(
        f"\n[dim]Next step:\n"
        f"  ddoc analyze drift --data-path-ref {ref_dir} --data-path-cur {cur_dir} --json --quiet[/dim]"
    )
