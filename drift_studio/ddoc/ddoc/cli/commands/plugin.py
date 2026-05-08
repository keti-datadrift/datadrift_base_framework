"""Plugin management commands"""
from typing import Optional
import typer
from rich import print
from .utils import get_pmgr, _pretty


def plugin_list_command():
    """
    List all installed plugins (without loading heavy dependencies).
    
    This command uses entry point metadata only, avoiding expensive imports
    like PyTorch and scikit-learn for fast execution.
    """
    print("[bold cyan]🔌 Installed Plugins:[/bold cyan]")

    # Use importlib.metadata to read entry points without loading plugins
    import importlib.metadata
    
    try:
        entry_points = importlib.metadata.entry_points(group="ddoc")
    except Exception as e:
        print(f"[red]❌ Failed to read plugins: {e}[/red]")
        return
    
    # Convert to list for compatibility with older Python versions
    plugins = list(entry_points) if hasattr(entry_points, '__iter__') else entry_points
    
    if plugins:
        print(f"\n[bold]Found {len(plugins)} plugins:[/bold]")
        print("-" * 60)
        print(f"{'Name':<20} {'Type':<15} {'Status':<10}")
        print("-" * 60)
        
        for ep in plugins:
            name = ep.name
            # Try to get plugin type from name
            if 'vision' in name.lower():
                plugin_type = "vision"
            elif 'yolo' in name.lower():
                plugin_type = "object-detect"
            elif 'nlp' in name.lower():
                plugin_type = "nlp"
            elif 'core' in name.lower() or 'builtin' in name.lower():
                plugin_type = "core"
            else:
                plugin_type = "extension"
            
            status = "installed"
            
            print(f"{name:<20} {plugin_type:<15} {status:<10}")
        
        print("-" * 60)
        print("\n[dim]💡 Tip: Use 'ddoc plugin info <name>' for detailed information[/dim]")
    else:
        print("  No plugins installed.")


def plugin_detectors_command():
    """Round-13 — print every plugin's advertised detector preset.

    Reads each registered plugin's ``ddoc_supported_detectors`` hookimpl
    (Gap 5) and prints a consolidated table. Use this to find the right
    ``--detector`` value before running ``ddoc analyze drift``.

    Plugins that don't implement the registry hook are listed as
    "(no preset declared)" — their per-plugin runtime validation
    (Round-11/12) still works.
    """
    pmgr = get_pmgr()
    pm = pmgr.pm
    try:
        decls = pm.hook.ddoc_supported_detectors()
    except Exception as e:
        print(f"[red]❌ Failed to gather detector registry: {e}[/red]")
        return
    decls = [d for d in (decls or []) if isinstance(d, dict)]

    print("[bold cyan]🎯 Detector preset registry[/bold cyan]\n")
    if not decls:
        print("  (no plugin declared any supported detectors)")
        return

    for d in decls:
        modality = d.get("modality", "?")
        default = d.get("default", "?")
        supported = d.get("supported", [])
        notes = d.get("notes", "")
        print(f"[bold yellow]{modality}[/bold yellow]  default = [bold]{default}[/bold]")
        print("  supported: " + ", ".join(f"[cyan]{s}[/cyan]" for s in supported))
        if notes:
            print(f"  [dim]{notes}[/dim]")
        print()
    print("[dim]💡 Tip: ddoc analyze drift --detector <strategy> ...[/dim]")


def plugin_install_command(
    package: str = typer.Argument(..., help="PyPI package name or PEP 508 requirement (e.g. ddoc-plugin-vision, 'ddoc-plugin-text==1.0', 'git+https://...')"),
    editable: bool = typer.Option(False, "-e", "--editable", help="Install in editable mode (for local plugin checkouts)"),
    upgrade: bool = typer.Option(False, "-U", "--upgrade", help="Pass --upgrade to pip"),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Suppress pip's per-step output"),
):
    """Install a ddoc plugin via pip.

    Round-10 — promoted from doc-only example to a real subcommand.
    Thin wrapper over ``pip install`` so users can stay inside the
    ddoc CLI for plugin lifecycle.

    Examples:
        ddoc plugin install ddoc-plugin-text
        ddoc plugin install -e plugins/ddoc-plugin-vision
        ddoc plugin install -U ddoc-plugin-vision
    """
    import sys
    import subprocess
    cmd = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    if editable:
        cmd.append("-e")
    if quiet:
        cmd.append("-q")
    cmd.append(package)

    print(f"[cyan]📦 {' '.join(cmd[3:])}[/cyan]")
    try:
        proc = subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print("[red]❌ pip not found in this Python environment[/red]")
        raise typer.Exit(code=1)

    if proc.returncode != 0:
        print(f"[red]❌ pip install failed (exit {proc.returncode})[/red]")
        raise typer.Exit(code=proc.returncode)

    print(f"[green]✅ Installed {package}[/green]")
    print("[dim]💡 Run 'ddoc plugin list' to confirm the new entry point is discovered.[/dim]")


def plugin_info_command(
    plugin_name: Optional[str] = typer.Argument(None, help="Specific plugin name to show info for")
):
    """
    Show detailed information about plugins.
    
    Examples:
        ddoc plugin info
        ddoc plugin info ddoc_vision
    """
    print("[bold magenta]🔍 Plugin Information[/bold magenta]")
    
    # Get metadata from all plugins
    metadata_list = get_pmgr().hook.ddoc_get_metadata()
    
    if not metadata_list:
        print("[yellow]No plugins provided metadata.[/yellow]")
        return
    
    if plugin_name:
        # Show specific plugin info
        plugin_metadata = next(
            (meta for meta in metadata_list if meta.get('name') == plugin_name),
            None
        )
        
        if plugin_metadata:
            print(f"\n[bold]Plugin: {plugin_name}[/bold]")
            print(_pretty(plugin_metadata))
        else:
            print(f"[red]❌ Plugin '{plugin_name}' not found.[/red]")
    else:
        # Show all plugins metadata
        print(f"\n[bold]All Plugins Metadata ({len(metadata_list)}):[/bold]")
        print(_pretty({"plugins_metadata": metadata_list}))

