"""Unified snapshot management command with hybrid structure"""
from typing import Optional, List
import typer
from rich import print


# Create Typer app for snapshot commands
snapshot_app = typer.Typer(
    help="Snapshot management - create, list, inspect, and checkout snapshots"
)


# ========================================================================
# 핵심 기능 - 서브 커맨드
# ========================================================================

@snapshot_app.command("create")
def create_snapshot(
    message: str = typer.Option(..., "-m", "--message", help="Snapshot description message"),
    alias: Optional[str] = typer.Option(None, "-a", "--alias", help="Alias for this snapshot"),
    no_auto_commit: bool = typer.Option(
        False, "--no-auto-commit",
        help="Skip the automatic dvc add + git commit step. By default (Round-5 onward) auto-commit is safe on a clean working tree (it detects 'nothing to commit' and skips); use this flag only if you want to stage changes manually first.",
    ),
):
    """Create a new snapshot.

    Default flow auto-commits any data/code changes via dvc add + git
    commit before recording the snapshot. ``--no-auto-commit`` opts out
    of that and requires the working tree to be clean (or you manage
    staging yourself); the snapshot then records the current HEAD.
    """
    from ddoc.core.snapshot_service import get_snapshot_service
    
    snapshot_service = get_snapshot_service()
    
    print(f"[cyan]📸 Creating snapshot...[/cyan]\n")
    result = snapshot_service.create_snapshot(
        message, 
        alias=alias,
        auto_commit=not no_auto_commit
    )
    
    if not result["success"]:
        print(f"[red]❌ Snapshot creation failed: {result['error']}[/red]")
        raise typer.Exit(code=1)
    
    print(f"[green]✅ Snapshot created successfully![/green]\n")
    print(f"[bold]Snapshot ID:[/bold] {result['snapshot_id']}")
    if result.get("alias"):
        print(f"[bold]Alias:[/bold] {result['alias']}")
    print(f"[bold]Message:[/bold] {result['message']}")
    print(f"[bold]Git commit:[/bold] {result['git_commit']}")
    print(f"[bold]Data hash:[/bold] {result['data_hash']}")
    print()


@snapshot_app.command("list")
def list_snapshots(
    oneline: bool = typer.Option(False, "--oneline", help="Show compact one-line format"),
    limit: Optional[int] = typer.Option(None, "-n", "--limit", help="Limit number of snapshots shown"),
):
    """List all snapshots"""
    from ddoc.core.snapshot_service import get_snapshot_service
    
    snapshot_service = get_snapshot_service()
    result = snapshot_service.list_snapshots(limit=limit)
    
    if not result["success"]:
        print(f"[red]❌ Failed to list snapshots: {result['error']}[/red]")
        raise typer.Exit(code=1)
    
    if result["count"] == 0:
        print("[yellow]No snapshots found. Create one with 'ddoc snapshot create -m \"message\"'[/yellow]")
        return
    
    print(f"[bold cyan]Snapshots[/bold cyan] ({result['count']} total)\n")
    
    for snap in result["snapshots"]:
        if oneline:
            alias_str = f" ({snap['alias']})" if snap['alias'] else ""
            print(f"{snap['snapshot_id']}{alias_str} - {snap['description'][:50]}")
        else:
            print(f"[bold yellow]{snap['snapshot_id']}[/bold yellow]", end="")
            if snap['alias']:
                print(f" [bold cyan]({snap['alias']})[/bold cyan]", end="")
            print()
            print(f"  {snap['description']}")
            print(f"  {snap['created_at']} | Git: {snap['git_commit']} | Data: {snap['data_hash']}")
            print()


@snapshot_app.command("inspect")
def inspect_snapshot(
    version: str = typer.Argument(..., help="Snapshot ID or alias"),
):
    """Show detailed information about a snapshot"""
    from ddoc.core.snapshot_service import get_snapshot_service
    
    snapshot_service = get_snapshot_service()
    
    snap_id = snapshot_service._resolve_version(version)
    if not snap_id:
        print(f"[red]❌ Snapshot '{version}' not found[/red]")
        raise typer.Exit(code=1)
    
    snap = snapshot_service._load_snapshot(snap_id)
    if not snap:
        print(f"[red]❌ Failed to load snapshot {snap_id}[/red]")
        raise typer.Exit(code=1)
    
    print(f"[bold cyan]Snapshot Details[/bold cyan]\n")
    print(f"[bold]ID:[/bold] {snap.snapshot_id}")
    if snap.alias:
        print(f"[bold]Alias:[/bold] {snap.alias}")
    print(f"[bold]Created:[/bold] {snap.created_at}")
    print(f"[bold]Description:[/bold] {snap.description}\n")
    
    print(f"[bold]Data:[/bold]")
    print(f"  Hash: {snap.data.dvc_hash}")
    print(f"  Contents: {', '.join(snap.data.contents) if snap.data.contents else 'none'}")
    if snap.data.stats:
        print(f"  Files: {snap.data.stats.get('total_files', 0)}")
        print(f"  Size: {snap.data.stats.get('total_size_mb', 0)} MB")
    
    print(f"\n[bold]Code:[/bold]")
    print(f"  Git: {snap.code.git_rev[:7]} ({snap.code.branch})")
    print(f"  Files: {len(snap.code.files)}")
    
    if snap.experiment:
        print(f"\n[bold]Experiment:[/bold]")
        print(f"  ID: {snap.experiment.id}")
        if snap.experiment.metrics:
            print(f"  Metrics:")
            for key, val in snap.experiment.metrics.items():
                print(f"    {key}: {val}")
    
    print()


@snapshot_app.command("checkout")
def checkout_snapshot(
    version: str = typer.Argument(..., help="Snapshot ID or alias"),
    force: bool = typer.Option(False, "-f", "--force", help="Force checkout even with uncommitted changes"),
):
    """Restore (checkout) a snapshot"""
    from ddoc.core.snapshot_service import get_snapshot_service
    
    snapshot_service = get_snapshot_service()
    
    print(f"[cyan]🔄 Restoring snapshot: {version}[/cyan]\n")
    result = snapshot_service.restore_snapshot(version, force=force)
    
    if not result["success"]:
        print(f"[red]❌ Snapshot restore failed: {result['error']}[/red]")
        raise typer.Exit(code=1)
    
    print(f"[green]✅ Snapshot restored successfully![/green]\n")
    print(f"[bold]Snapshot ID:[/bold] {result['snapshot_id']}")
    if result.get("alias"):
        print(f"[bold]Alias:[/bold] {result['alias']}")
    print(f"[bold]Description:[/bold] {result['description']}")
    print()


# ========================================================================
# 부가 기능 - 옵션으로 처리
# ========================================================================

def _diff_snapshots(version1: str, version2: str) -> None:
    """Shared snapshot-diff logic, callable from either the
    ``--diff v1 v2`` parent option (legacy) or the new
    ``ddoc snapshot diff v1 v2`` subcommand (Round-8). Prints the diff
    or exits non-zero on failure."""
    from ddoc.core.snapshot_service import get_snapshot_service
    from ddoc.core.git_service import get_git_service

    snapshot_service = get_snapshot_service()
    print(f"[cyan]🔍 Comparing snapshots: {version1} vs {version2}[/cyan]\n")

    v1 = snapshot_service._resolve_version(version1)
    v2 = snapshot_service._resolve_version(version2)

    if not v1:
        print(f"[red]❌ Snapshot '{version1}' not found[/red]")
        raise typer.Exit(code=1)
    if not v2:
        print(f"[red]❌ Snapshot '{version2}' not found[/red]")
        raise typer.Exit(code=1)

    snap1 = snapshot_service._load_snapshot(v1)
    snap2 = snapshot_service._load_snapshot(v2)

    print(f"[bold]Data Changes:[/bold]")
    if snap1.data.dvc_hash != snap2.data.dvc_hash:
        print(f"  [yellow]Data hash changed[/yellow]")
        print(f"    {v1}: {snap1.data.dvc_hash[:7]}")
        print(f"    {v2}: {snap2.data.dvc_hash[:7]}")
    else:
        print(f"  [green]No data changes[/green]")

    print(f"\n[bold]Code Changes:[/bold]")
    git_service = get_git_service()
    git_diff = git_service.diff(snap1.code.git_rev, snap2.code.git_rev)
    if git_diff.get("has_changes"):
        print(f"[yellow]{git_diff['stat']}[/yellow]")
    else:
        print(f"  [green]No code changes[/green]")
    print()


@snapshot_app.command("diff")
def diff_snapshots(
    version1: str = typer.Argument(..., help="First snapshot ID or alias"),
    version2: str = typer.Argument(..., help="Second snapshot ID or alias"),
):
    """Compare two snapshots (data + code).

    Round-8 — promoted from the parent's ``--diff`` option to a proper
    subcommand for consistency with create/list/inspect/checkout. The
    legacy ``ddoc snapshot --diff v1 v2`` form still works.
    """
    _diff_snapshots(version1, version2)


@snapshot_app.callback(invoke_without_command=True)
def snapshot(
    ctx: typer.Context,
    # List options (for backward compatibility)
    oneline: bool = typer.Option(False, "--oneline", help="Show compact one-line format"),
    limit: Optional[int] = typer.Option(None, "-n", "--limit", help="Limit number of snapshots shown"),
    
    # Additional options
    diff: Optional[List[str]] = typer.Option(None, "--diff", help="Compare two snapshots (provide 2 versions)"),
    graph: bool = typer.Option(False, "--graph", help="Show snapshot lineage graph"),
    delete: Optional[str] = typer.Option(None, "--delete", help="Delete a snapshot"),
    set_alias: Optional[List[str]] = typer.Option(None, "--set-alias", help="Set alias (version alias)"),
    unalias: Optional[str] = typer.Option(None, "--unalias", help="Remove alias"),
    show_aliases: bool = typer.Option(False, "--show-aliases", help="Show all aliases"),
    rename: Optional[str] = typer.Option(None, "--rename", help="Edit snapshot description (requires version argument)"),
    verify: Optional[str] = typer.Option(None, "--verify", help="Verify snapshot integrity"),
    verify_all: bool = typer.Option(False, "--verify-all", help="Verify all snapshots"),
    prune: bool = typer.Option(False, "--prune", help="Identify orphaned snapshots"),
    force: bool = typer.Option(False, "-f", "--force", help="Force operation"),
):
    """
    Snapshot management command.
    
    Core commands (most frequently used):
      create    Create a new snapshot
      list      List all snapshots
      inspect   Show detailed information about a snapshot
      checkout  Restore (checkout) a snapshot
    
    Additional options (less frequently used):
      --diff, --graph, --delete, --set-alias, --unalias, --show-aliases,
      --rename, --verify, --verify-all, --prune
    """
    # 서브 커맨드가 호출된 경우 여기서는 처리하지 않음
    if ctx.invoked_subcommand is not None:
        return
    
    from ddoc.core.snapshot_service import get_snapshot_service
    from ddoc.core.git_service import get_git_service
    
    snapshot_service = get_snapshot_service()
    
    # 옵션이 하나도 지정되지 않은 경우 에러 처리
    has_option = any([
        diff, graph, delete, set_alias, unalias, show_aliases, 
        rename, verify, verify_all, prune
    ])
    
    if not has_option:
        print("[red]❌ Error: No command or option specified.[/red]")
        print("\n[bold]Core commands:[/bold]")
        print("  ddoc snapshot create -m \"message\"    Create a new snapshot")
        print("  ddoc snapshot list                    List all snapshots")
        print("  ddoc snapshot inspect <version>       Show snapshot details")
        print("  ddoc snapshot checkout <version>    Restore a snapshot")
        print("\n[bold]Additional options:[/bold]")
        print("  ddoc snapshot --diff <v1> <v2>         Compare two snapshots")
        print("  ddoc snapshot --graph                  Show lineage graph")
        print("  ddoc snapshot --delete <version>       Delete a snapshot")
        print("  ddoc snapshot --verify <version>       Verify snapshot integrity")
        print("  ddoc snapshot --prune                  Identify orphaned snapshots")
        print("\nUse 'ddoc snapshot --help' for more information.")
        raise typer.Exit(code=1)
    
    # ========================================================================
    # COMPARE SNAPSHOTS (legacy --diff option — kept for backward compat;
    # prefer ``ddoc snapshot diff <v1> <v2>`` subcommand introduced in Round-8)
    # ========================================================================
    if diff and len(diff) >= 2:
        _diff_snapshots(diff[0], diff[1])
        return
    
    # ========================================================================
    # SHOW LINEAGE GRAPH
    # ========================================================================
    if graph:
        print(f"[cyan]📊 Snapshot Lineage Graph[/cyan]\n")
        result = snapshot_service.get_lineage_graph()
        
        if not result["success"]:
            print(f"[red]❌ Failed to get lineage: {result['error']}[/red]")
            raise typer.Exit(code=1)
        
        if result["total_nodes"] == 0:
            print("[yellow]No snapshots found[/yellow]")
            return
        
        print(f"[bold]Total Snapshots:[/bold] {result['total_nodes']}")
        print(f"[bold]Total Relationships:[/bold] {result['total_edges']}\n")
        
        # Simple text-based graph
        for node in result["nodes"]:
            alias_str = f" ({node['alias']})" if node['alias'] else ""
            print(f"[bold yellow]{node['id']}[/bold yellow]{alias_str}")
            print(f"  {node['description']}")
            print(f"  Git: {node['git_commit']} | Data: {node['data_hash']}")
            
            # Show edges
            for edge in result["edges"]:
                if edge["from"] == node["id"]:
                    print(f"  └──> {edge['to']}")
            print()
        return
    
    # ========================================================================
    # DELETE SNAPSHOT
    # ========================================================================
    if delete:
        if not force:
            response = input(f"⚠️  Delete snapshot '{delete}'? This cannot be undone. [y/N]: ")
            if response.lower() != 'y':
                print("[yellow]Cancelled[/yellow]")
                return
        
        result = snapshot_service.delete_snapshot(delete, force=force)
        
        if not result["success"]:
            print(f"[red]❌ Deletion failed: {result['error']}[/red]")
            raise typer.Exit(code=1)
        
        print(f"[green]✅ Snapshot {result['snapshot_id']} deleted[/green]")
        return
    
    # ========================================================================
    # ALIAS MANAGEMENT
    # ========================================================================
    if set_alias and len(set_alias) >= 2:
        ver, al = set_alias[0], set_alias[1]
        if not (snapshot_service.snapshots_dir / f"{ver}.yaml").exists():
            print(f"[red]❌ Snapshot '{ver}' not found[/red]")
            raise typer.Exit(code=1)
        
        snapshot_service._set_alias(al, ver)
        print(f"[green]✅ Alias '{al}' set to {ver}[/green]")
        return
    
    if unalias:
        aliases = snapshot_service._load_aliases()
        if aliases.remove_alias(unalias):
            snapshot_service._save_aliases(aliases)
            print(f"[green]✅ Alias '{unalias}' removed[/green]")
        else:
            print(f"[yellow]⚠️  Alias '{unalias}' not found[/yellow]")
        return
    
    if show_aliases:
        result = snapshot_service.list_snapshots()
        if result["success"]:
            print(f"[bold cyan]Snapshot Aliases[/bold cyan]\n")
            has_aliases = False
            for snap in result["snapshots"]:
                if snap['alias']:
                    print(f"{snap['alias']:20s} → {snap['snapshot_id']}")
                    has_aliases = True
            if not has_aliases:
                print("[yellow]No aliases defined[/yellow]")
        return
    
    # ========================================================================
    # EDIT DESCRIPTION
    # ========================================================================
    # Note: --rename 기능은 현재 구조에서는 옵션으로 처리하기 어려움
    # 필요시 서브 커맨드로 추가 가능: ddoc snapshot edit <version> -m "new description"
    if rename:
        print("[yellow]⚠️  Warning: --rename option is deprecated.[/yellow]")
        print("   This feature will be available as a subcommand in the future.")
        print("   For now, please edit the snapshot YAML file directly in .ddoc/snapshots/")
        raise typer.Exit(code=1)
    
    # ========================================================================
    # VERIFY
    # ========================================================================
    if verify:
        result = snapshot_service.verify_snapshot(verify)
        
        if not result["success"]:
            print(f"[red]❌ Verification failed: {result.get('error', 'Unknown error')}[/red]")
            raise typer.Exit(code=1)
        
        if result["success"] and not result.get("issues"):
            print(f"[green]✅ Snapshot {result['snapshot_id']} is valid[/green]")
        else:
            print(f"[yellow]⚠️  Issues found in {result['snapshot_id']}:[/yellow]")
            for issue in result.get("issues", []):
                print(f"  - {issue}")
        return
    
    if verify_all:
        result = snapshot_service.verify_all_snapshots()
        
        if not result["success"]:
            print(f"[red]❌ Verification failed: {result['error']}[/red]")
            raise typer.Exit(code=1)
        
        print(f"[bold cyan]Snapshot Verification Results[/bold cyan]\n")
        print(f"Total: {result['total']} | Valid: {result['valid']} | Invalid: {result['invalid']}\n")
        
        for item in result["results"]:
            status = "[green]✅[/green]" if item["valid"] else "[red]❌[/red]"
            print(f"{status} {item['snapshot_id']}")
            if item["issues"]:
                for issue in item["issues"]:
                    print(f"    - {issue}")
        return
    
    # ========================================================================
    # PRUNE
    # ========================================================================
    if prune:
        result = snapshot_service.prune_snapshots()
        
        if not result["success"]:
            print(f"[red]❌ Prune failed: {result['error']}[/red]")
            raise typer.Exit(code=1)
        
        print(f"[bold cyan]Snapshot Prune Analysis[/bold cyan]\n")
        print(f"Total Snapshots: {result['total_snapshots']}")
        print(f"Referenced: {result['referenced']}")
        print(f"Orphaned: {result['orphaned']}\n")
        
        if result["orphaned_list"]:
            print("[yellow]Orphaned snapshots:[/yellow]")
            for snap_id in result["orphaned_list"]:
                print(f"  - {snap_id}")
            print(f"\nUse 'ddoc snapshot --delete <id>' to remove them.")
        else:
            print("[green]No orphaned snapshots found[/green]")
        return


# Export the app for registration (both names for compatibility)
snapshot = snapshot_app
__all__ = ["snapshot_app", "snapshot"]
