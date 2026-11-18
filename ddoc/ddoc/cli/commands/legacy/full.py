from __future__ import annotations
import json
import typer
from typing import Optional, Any, List, Dict
from pathlib import Path
from datetime import datetime
import os
import shutil
import subprocess
from rich import print
# load_params_yaml 함수를 직접 구현
def load_params_yaml():
    """Load params.yaml file"""
    try:
        import yaml
        with open("params.yaml", 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Warning: Could not load params.yaml: {e}")
        return {}

def get_dataset_path(dataset_name: str) -> Optional[str]:
    """Get dataset path using new mapping system with params.yaml fallback"""
    # Check if it's a direct path
    if Path(dataset_name).exists():
        return dataset_name
    
    # Try new mapping system first
    from ddoc.core.metadata_service import get_metadata_service
    metadata_service = get_metadata_service()
    mapping = metadata_service.get_dataset_mapping(dataset_name)
    if mapping:
        return mapping.get('dataset_path')
    
    # Fallback to params.yaml (legacy support)
    params = load_params_yaml()
    dataset_config = next(
        (ds for ds in params.get('datasets', []) if ds['name'] == dataset_name),
        None
    )
    if dataset_config:
        return dataset_config['path']
    
    return None

# 플러그인 매니저 인스턴스를 지연 로딩합니다.
# 모듈 레벨에서 호출하면 순환 import 문제가 발생할 수 있습니다.
_pmgr = None

def get_pmgr():
    """Get or create plugin manager instance (lazy loading)"""
    global _pmgr
    if _pmgr is None:
        from ddoc.core.plugins import get_plugin_manager
        _pmgr = get_plugin_manager()
    return _pmgr

# 새로운 명령어 구조를 위한 서브 Typer 앱 생성
dataset_app = typer.Typer(help="Dataset management commands (add, commit, status, list, tag, timeline, checkout)")
tag_app = typer.Typer(
    help="Dataset version tag management commands (list, rename)",
    invoke_without_command=False
)
analyze_app = typer.Typer(help="Data analysis commands (eda, drift)")
exp_app = typer.Typer(help="Experiment management commands (run, list, show, compare, status)")
plugin_app = typer.Typer(help="Plugin management commands (list, info)")
lineage_app = typer.Typer(help="Lineage tracking commands (show, graph, impact)")

# dataset tag 서브앱을 dataset 앱에 등록
dataset_app.add_typer(tag_app, name="tag")

# 통합된 서비스 인스턴스들 (지연 초기화)
_core_ops = None
_metadata_service = None
_dataset_service = None
_experiment_service = None

def get_core_ops():
    """Get core_ops instance (lazy initialization)"""
    global _core_ops
    if _core_ops is None:
        from ddoc.ops.core_ops import CoreOpsPlugin
        _core_ops = CoreOpsPlugin()
    return _core_ops

def get_metadata_service_instance():
    """Get metadata service instance (lazy initialization)"""
    global _metadata_service
    if _metadata_service is None:
        from ddoc.core.metadata_service import get_metadata_service
        _metadata_service = get_metadata_service()
    return _metadata_service

def get_dataset_service_instance():
    """Get dataset service instance (lazy initialization)"""
    global _dataset_service
    if _dataset_service is None:
        from ddoc.core.dataset_service import get_dataset_service
        _dataset_service = get_dataset_service()
    return _dataset_service

def get_experiment_service_instance():
    """Get experiment service instance (lazy initialization)"""
    global _experiment_service
    if _experiment_service is None:
        from ddoc.core.experiment_service import get_experiment_service
        _experiment_service = get_experiment_service()
    return _experiment_service

# --- JSON Pretty Print 헬퍼 함수 ---
def _pretty(x: Any) -> str:
    """JSON 또는 객체를 보기 좋게 출력"""
    try:
        # ensure_ascii=False를 사용하여 한글 깨짐 방지
        return json.dumps(x, indent=2, ensure_ascii=False)
    except Exception:
        return str(x)

# ============================================================================
# Dataset Commands (통합된 dataset 커맨드)
# ============================================================================

@dataset_app.command("add")
def dataset_add_command(
    path: str = typer.Argument(..., help="Path to dataset directory"),
    formats: List[str] = typer.Option(['.jpg', '.png'], "--format", "-f", help="File formats to include"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="YOLO config file name"),
):
    """
    Stage a dataset for commit (new or modified).
    Dataset name is automatically derived from the folder name.
    
    📝 Dataset Naming:
    - Dataset name is automatically the folder name
    - For meaningful labels, use version aliases:
      1. Commit: ddoc dataset commit -m "message" -a "alias_name"
      2. Or later: ddoc dataset tag rename <name> <version> -a <alias>
      3. Use alias: ddoc analyze eda <name>@<alias>
    
    Examples:
        ddoc dataset add ./data/my_data              # name = 'my_data'
        ddoc dataset add /path/to/train_set          # name = 'train_set'
        ddoc dataset add ./data/my_data              # modify existing 'my_data'
        
        # After commit, add meaningful alias
        ddoc dataset commit -m "Best accuracy" -a best_acc_sampled
        ddoc analyze eda my_data@best_acc_sampled
    """
    try:
        # Extract dataset name from path
        dataset_path = Path(path)
        name = dataset_path.name  # 자동으로 폴더명 사용
        
        print(f"[cyan]📦 Dataset name: {name}[/cyan]")
        print(f"[cyan]📁 Path: {path}[/cyan]")
        
        # Stage the dataset
        res = get_dataset_service_instance().stage_dataset(
            name=name,
            path=path,
            formats=formats,
            config=config
        )
        
        if not res.get('success'):
            print(f"[bold red]❌ Error:[/bold red] {res.get('error')}")
            raise typer.Exit(code=1)
            
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@dataset_app.command("list")
def dataset_list_command():
    """
    List all registered datasets.
    """
    print("[bold cyan]📦 Registered Datasets:[/bold cyan]")
    try:
        datasets = get_dataset_service_instance().list_datasets()
        if datasets:
            for ds in datasets:
                print(f"\n[green]• {ds['name']}[/green]")
                print(f"  📁 Path: {ds['path']}")
                print(f"  📄 DVC File: {ds['dvc_file']}")
                if ds.get('registered_at'):
                    print(f"  📅 Registered: {ds['registered_at']}")
                if ds.get('formats'):
                    print(f"  📋 Formats: {', '.join(ds['formats'])}")
        else:
            print("  No datasets registered yet.")
            print("  Use 'ddoc dataset add <name> <path>' to register a dataset.")
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")




@dataset_app.command("commit")
def dataset_commit_command(
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Version tag (e.g., v1.0)"),
    alias: Optional[str] = typer.Option(None, "--alias", "-a", help="Alias for this version (e.g., best_acc_sampled)"),
):
    """
    Commit staged dataset changes and create versions.
    Optionally assign an alias to the new version for easier reference.
    
    Examples:
        ddoc dataset commit -m "Initial dataset"
        ddoc dataset commit -m "Update images" -t v1.1
        ddoc dataset commit -m "Best accuracy" -a best_acc_sampled
        ddoc dataset commit -m "Production" -t v2.0 -a production
    """
    print(f"[bold cyan]Committing staged datasets...[/bold cyan]")
    try:
        result = get_dataset_service_instance().commit_staged_datasets(
            message=message,
            tag=tag
        )
        
        if not result.get('success'):
            print(f"[bold red]❌ Error:[/bold red] {result.get('error')}")
            raise typer.Exit(code=1)
        
        # Print committed datasets
        committed = result.get('committed', [])
        errors = result.get('errors', [])
        
        if committed:
            print(f"\n[green]✅ Successfully committed {len(committed)} dataset(s):[/green]")
            for dataset in committed:
                op_str = "new" if dataset['operation'] == 'new' else "modified"
                print(f"  [{dataset['name']} {dataset['version']}] ({op_str})")
            
            # Apply alias if provided
            if alias:
                print(f"\n[cyan]🏷️ Applying alias: {alias}[/cyan]")
                for dataset in committed:
                    name = dataset['name']
                    version = dataset['version']
                    
                    alias_result = get_dataset_service_instance().set_version_alias(
                        name, version, alias
                    )
                    if alias_result.get('success'):
                        print(f"[green]✅ Alias set: {name}@{version} → {alias}[/green]")
                    else:
                        print(f"[yellow]⚠️ Failed to set alias for {name}@{version}: {alias_result.get('error')}[/yellow]")
        
        if errors:
            print(f"\n[yellow]⚠️ Errors during commit:[/yellow]")
            for error in errors:
                print(f"  {error}")
        
        print(f"\n[dim]Message: {message}[/dim]")
            
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@dataset_app.command("status")
def dataset_status_command():
    """
    Show status of all datasets (git status style).
    
    Shows:
    - Staged changes (ready to commit)
    - Unstaged changes (modifications not yet staged)
    - Untracked datasets
    """
    print(f"[bold cyan]Dataset Status[/bold cyan]\n")
    try:
        status = get_dataset_service_instance().get_full_status()
        
        if not status.get('success'):
            print(f"[bold red]❌ Error:[/bold red] {status.get('error')}")
            return
        
        staged = status.get('staged', {})
        unstaged = status.get('unstaged', {})
        untracked = status.get('untracked', [])
        
        staged_new = staged.get('new', [])
        staged_modified = staged.get('modified', [])
        unstaged_modified = unstaged.get('modified', [])
        
        # Show staged changes
        if staged_new or staged_modified:
            print("[bold green]Changes to be committed:[/bold green]")
            print("  [dim](use \"ddoc dataset unstage <name>\" to unstage)[/dim]\n")
            
            for dataset in staged_new:
                print(f"  [green]new dataset:[/green]  {dataset['name']}")
            
            for dataset in staged_modified:
                hash_display = dataset.get('current_hash', 'N/A')[:8]
                print(f"  [green]modified:[/green]     {dataset['name']} (hash: {hash_display}...)")
            
            print()
        
        # Show unstaged changes
        if unstaged_modified:
            print("[bold yellow]Changes not staged for commit:[/bold yellow]")
            print("  [dim](use \"ddoc dataset add <name>\" to stage changes)[/dim]\n")
            
            for dataset in unstaged_modified:
                old_hash = dataset.get('old_hash', 'N/A')[:8]
                new_hash = dataset.get('new_hash', 'N/A')[:8]
                print(f"  [yellow]modified:[/yellow]     {dataset['name']} ({old_hash}... → {new_hash}...)")
            
            print()
        
        # Show untracked
        if untracked:
            print("[bold]Untracked datasets:[/bold]")
            print("  [dim](use \"ddoc dataset add <name> <path>\" to track)[/dim]\n")
            
            for dataset in untracked:
                print(f"  {dataset}")
            
            print()
        
        # If nothing to show
        if not (staged_new or staged_modified or unstaged_modified or untracked):
            print("[green]No changes detected[/green]")
            print("  [dim]All datasets are clean and up to date[/dim]")
            
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")


@dataset_app.command("unstage")
def dataset_unstage_command(
    name: str = typer.Argument(..., help="Dataset name to unstage"),
):
    """
    Remove a dataset from staging area.
    
    Example:
        ddoc dataset unstage my_data
    """
    try:
        result = get_dataset_service_instance().staging_service.unstage_dataset(name)
        
        if result.get('success'):
            print(f"[green]✅ Unstaged: {name}[/green]")
        else:
            print(f"[bold red]❌ Error:[/bold red] {result.get('error')}")
            raise typer.Exit(code=1)
            
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(code=1)


def _resolve_dataset_reference(dataset_ref: str) -> Tuple[str, Optional[str]]:
    """
    Resolve dataset reference in format: name or name@version/alias
    
    Args:
        dataset_ref: Dataset reference string (e.g., 'my_data' or 'my_data@v1.0' or 'my_data@best_acc')
    
    Returns:
        Tuple of (dataset_name, version_or_alias)
    """
    if '@' in dataset_ref:
        parts = dataset_ref.split('@', 1)
        return parts[0], parts[1]
    return dataset_ref, None


def _resolve_version_identifier(dataset: str, identifier: str) -> str:
    """Resolve version identifier by alias if necessary."""
    dataset_service = get_dataset_service_instance()
    resolved = dataset_service.get_version_by_alias(dataset, identifier)
    return resolved or identifier


def _format_timestamp(ts: Optional[str]) -> str:
    if not ts:
        return "-"
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return ts
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _print_dataset_timeline(events: List[Dict[str, Any]], include_details: bool) -> None:
    icon_map = {
        'version': '📌',
        'analysis': '📈',
        'experiment': '🧪',
        'drift_analysis': '📊'
    }

    for event in events:
        event_type = event.get('event_type', 'unknown')
        icon = icon_map.get(event_type, '🔸')
        timestamp = _format_timestamp(event.get('timestamp'))

        if event_type == 'version':
            version = event.get('version') or '-'
            alias = event.get('alias')
            alias_display = f" (alias: {alias})" if alias else ""
            print(f"{icon} {timestamp} • Version {version}{alias_display}")

            metadata = event.get('metadata') or {}
            message = metadata.get('message')
            if message:
                print(f"   Message: {message}")
            hash_value = metadata.get('hash')
            if hash_value:
                print(f"   Hash: {hash_value[:8]}...")

            if include_details:
                for key, value in metadata.items():
                    if key in {'message', 'hash', 'alias'}:
                        continue
                    print(f"   {key}: {value}")
        else:
            name = event.get('name') or event.get('id')
            dataset_version = event.get('dataset_version') or event.get('version') or '-'
            relationship = event.get('relationship')
            relationship_display = f" [{relationship}]" if relationship else ""
            alias = event.get('alias')
            alias_display = f" (alias: {alias})" if alias else ""

            print(f"{icon} {timestamp} • {name}{relationship_display} (version: {dataset_version}{alias_display})")

            metadata = event.get('metadata') or {}
            if include_details and metadata:
                for key, value in metadata.items():
                    print(f"   {key}: {value}")


def _handle_version_rename(
    dataset: str,
    version_identifier: str,
    alias: Optional[str],
    remove_alias: bool
):
    if alias and remove_alias:
        raise typer.BadParameter("--alias와 --remove-alias를 동시에 사용할 수 없습니다.")
    if not alias and not remove_alias:
        raise typer.BadParameter("--alias 옵션 또는 --remove-alias 중 하나를 지정해야 합니다.")

    dataset_service = get_dataset_service_instance()
    actual_version = _resolve_version_identifier(dataset, version_identifier)

    versions = dataset_service.list_versions(dataset)
    version_entry = next((v for v in versions if v["version"] == actual_version), None)
    if not version_entry:
        raise typer.BadParameter(f"버전 '{version_identifier}'을(를) 찾을 수 없습니다.")

    target_alias = None if remove_alias else alias
    result = dataset_service.set_version_alias(dataset, actual_version, target_alias)

    if not result.get("success"):
        print(f"[bold red]❌ Error:[/bold red] {result.get('error')}")
        raise typer.Exit(code=1)

    alias_value = result.get("alias")
    alias_display = alias_value if alias_value else "(alias removed)"
    print(f"[green]✅ Version alias updated:[/green] {dataset}@{actual_version} → {alias_display}")


@tag_app.command("list")
def dataset_tag_list_command(
    name: str = typer.Argument(..., help="Dataset name"),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show full metadata"),
):
    """
    List dataset version tags with alias information.
    
    Example:
        ddoc dataset tag list my_data
    """
    print(f"[bold cyan]Version tags for {name}[/bold cyan]")
    try:
        versions = get_dataset_service_instance().list_versions(name)
        if not versions:
            print(f"[yellow]No versions found for {name}[/yellow]")
            print(f"  [dim]Use 'ddoc dataset commit' to create the first version[/dim]")
            return

        for idx, version in enumerate(versions, start=1):
            alias = version.get("alias")
            alias_display = f" (alias: {alias})" if alias else ""
            print(f"{idx}. {version['version']}{alias_display}")
            if show_all:
                print(f"   Hash: {version['hash'][:8]}...")
                print(f"   Timestamp: {version['timestamp']}")
                message = version.get("message") or ""
                if message:
                    print(f"   Message: {message}")
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")


@tag_app.command("rename")
def dataset_tag_rename_command(
    name: str = typer.Argument(..., help="Dataset name"),
    version_identifier: str = typer.Argument(..., help="Version ID or alias to rename"),
    alias: Optional[str] = typer.Option(None, "--alias", "-a", help="New alias name"),
    remove_alias: bool = typer.Option(False, "--remove-alias", help="Remove alias from version"),
):
    """
    Assign or remove an alias for a dataset version tag.
    
    Examples:
        ddoc dataset tag rename my_data v1.0 -a stable
        ddoc dataset tag rename my_data stable --remove-alias
    """
    _handle_version_rename(name, version_identifier, alias, remove_alias)


@dataset_app.command("timeline")
def dataset_timeline_command(
    name: str = typer.Argument(..., help="Dataset name"),
    include_details: bool = typer.Option(False, "--details", "-d", help="Show detailed metadata for each event"),
):
    """Display dataset timeline including versions, analyses, experiments, and drift results."""
    print(f"[bold cyan]Dataset timeline for {name}[/bold cyan]")
    try:
        timeline = get_dataset_service_instance().get_dataset_timeline(name)

        if not timeline:
            print(f"[yellow]No timeline entries found for {name}[/yellow]")
            print(f"   Run 'ddoc dataset version create {name}' to create the first version")
            return

        _print_dataset_timeline(timeline, include_details)

    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")




@dataset_app.command("checkout")
def dataset_checkout_command(
    name: str = typer.Argument(..., help="Dataset name"),
    tag: str = typer.Argument(..., help="Version tag"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
    no_pull: bool = typer.Option(False, "--no-pull", help="Skip DVC pull from remote"),
    force: bool = typer.Option(False, "--force", help="Force checkout even with uncommitted changes"),
):
    """
    Checkout a specific dataset version.
    
    Automatically detects Git+DVC or DVC-only restore strategy based on version metadata.
    """
    print(f"[bold cyan]Checking out {name} version {tag}[/bold cyan]")
    
    if dry_run:
        print("[yellow]🔍 Dry run mode - no changes will be made[/yellow]")
    
    try:
        res = get_dataset_service_instance().checkout_version(
            name, tag, 
            pull=not no_pull, 
            dry_run=dry_run, 
            force=force
        )
        
        if res.get("success"):
            strategy = res.get("strategy", "unknown")
            print(f"[green]✅ Successfully checked out {name}@{tag}[/green]")
            print(f"   Strategy: {strategy}")
            
            if res.get("dry_run"):
                print(f"   {res.get('message', '')}")
            elif strategy == "git+dvc":
                git_ref = res.get("git_reference", "unknown")
                print(f"   Git reference: {git_ref}")
            elif strategy == "dvc-only":
                target_hash = res.get("target_hash", "unknown")
                print(f"   Target hash: {target_hash[:8]}...")
        else:
            print(f"[bold red]❌ Error:[/bold red] {res.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")

# ============================================================================
# Analyze Commands (EDA 및 Drift 분석)
# ============================================================================

@analyze_app.command("eda")
def analyze_eda_command(
    dataset: str = typer.Argument(..., help="Dataset name or name@version/alias (e.g., my_data@best_acc_sampled)"),
    invalidate_cache: bool = typer.Option(False, "--invalidate-cache", help="Invalidate existing cache before analysis"),
):
    """
    Run EDA analysis on a dataset (attribute analysis + embedding extraction + clustering).
    
    Supports version/alias reference: dataset_name@version or dataset_name@alias
    
    Examples:
        ddoc analyze eda my_data                    # Use current version
        ddoc analyze eda my_data@v1.0               # Specific version
        ddoc analyze eda my_data@best_acc_sampled   # Using alias
    
    Automatically detects file changes and validates cache integrity.
    """
    # Parse dataset reference
    dataset_name, version_or_alias = _resolve_dataset_reference(dataset)
    
    print(f"[bold cyan]Analyzing dataset: {dataset_name}[/bold cyan]")
    
    # Get dataset path using new mapping system
    dataset_path = get_dataset_path(dataset_name)
    
    if not dataset_path:
        print(f"[bold red]❌ Dataset '{dataset_name}' not found[/bold red]")
        print("   Run 'ddoc dataset add' first.")
        return
    
    # Check dataset version status
    try:
        from ddoc.core.version_service import get_version_service
        version_service = get_version_service()
        version_service.check_version_state(dataset_name)
        
        # Get current status
        status = version_service.get_dataset_status(dataset_name)
        
        # Resolve version/alias if provided
        if version_or_alias:
            # Try to resolve alias first
            resolved_version = version_service.get_dataset_version_by_alias(
                dataset_name, version_or_alias
            )
            if resolved_version:
                current_version = resolved_version
                print(f"📋 Resolved alias '{version_or_alias}' → {current_version}")
            else:
                # Assume it's a version tag
                current_version = version_or_alias
                print(f"📋 Using version: {current_version}")
        else:
            # Use current version
            current_version = status['current_version']
            print(f"📋 Current version: {current_version}")
        
        # Check for modifications and warn about cache
        if status.get('state') == 'modified':
            print(f"[yellow]⚠️ Dataset has uncommitted changes[/yellow]")
            if not invalidate_cache:
                print(f"   Consider using --invalidate-cache to ensure fresh analysis")
        
        # Invalidate cache if requested
        if invalidate_cache:
            print(f"[yellow]🗑️ Invalidating cache for {dataset}[/yellow]")
            try:
                # Installed plugin only (no local fallback)
                from ddoc_plugin_vision.cache_utils import get_cache_manager
                cache_manager = get_cache_manager(dataset_path)
                cache_manager.clear_all_cache()
                print(f"[green]✅ Cache invalidated[/green]")
            except Exception as e:
                if isinstance(e, ImportError):
                    print("[yellow]⚠️ Could not invalidate cache: Vision plugin not installed (pip install ddoc-plugin-vision)[/yellow]")
                else:
                    print(f"[yellow]⚠️ Could not invalidate cache: {e}[/yellow]")
        
    except Exception as e:
        print(f"[bold red]❌ Version check failed: {e}[/bold red]")
        return
    
    input_path = dataset_path
    output_path = f"analysis/{dataset_name}"
    
    # Call vision plugin eda_run
    try:
        res = get_pmgr().hook.eda_run(input_path=input_path, modality="image", output_path=output_path, version=current_version, dataset_name=dataset_name)
        print(_pretty(res))
        
        # Add analysis to lineage with version info
        if res:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            analysis_id = f"{dataset_name}@{current_version}_analysis_{timestamp}"
            analysis_name = f"{dataset_name}@{current_version} EDA"
            dataset_id = f"{dataset_name}@{current_version}"
            
            get_metadata_service_instance().add_analysis(
                analysis_id=analysis_id,
                analysis_name=analysis_name,
                dataset_id=dataset_id,
                metadata={
                    "output_path": output_path,
                    "metrics_file": res[0].get('metrics_file', 'unknown'),
                    "timestamp": timestamp
                }
            )
            
            print(f"✅ Analysis linked to dataset version {current_version}")
            
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()


@analyze_app.command("drift")
def analyze_drift_command(
    dataset1: str = typer.Argument(..., help="First dataset name or baseline dataset"),
    dataset2: Optional[str] = typer.Argument(None, help="Second dataset name (for cross-dataset drift)"),
    baseline: str = typer.Option("baseline", "--baseline", "-b", help="Baseline version (for same-dataset drift)"),
    current: str = typer.Option("latest", "--current", "-c", help="Current version (for same-dataset drift)"),
    set_baseline: bool = typer.Option(False, "--set-baseline", help="Set current as baseline"),
):
    """
    Detect drift between datasets or dataset versions.
    
    Examples:
        ddoc analyze drift my_dataset                    # Same dataset, version-based drift
        ddoc analyze drift my_dataset --baseline v1.0   # Specific baseline version
        ddoc analyze drift dataset1 dataset2            # Cross-dataset drift
    """
    # Load params.yaml for drift config
    params = load_params_yaml()
    
    if dataset2 is None:
        # Same dataset, version-based drift
        print(f"[bold cyan]Drift detection for: {dataset1} (version-based)[/bold cyan]")
        
        # Get dataset path using new mapping system
        data_path = get_dataset_path(dataset1)
        
        if not data_path:
            print(f"[bold red]❌ Dataset '{dataset1}' not found[/bold red]")
            return
        output_path = f"analysis/{dataset1}/drift/"
        
        # Load drift config
        drift_cfg = dict(params.get('drift', {}) or {})
        drift_cfg['baseline_version'] = baseline
        drift_cfg['current_version'] = current

        baseline_attr_cache = baseline_emb_cache = None
        current_attr_cache = current_emb_cache = None

        try:
            from ddoc_plugin_vision.cache_utils import get_cache_repository

            repo = get_cache_repository(data_path, dataset_name=dataset1)
            baseline_attr_cache = repo.load(baseline, "attribute_analysis")
            baseline_emb_cache = repo.load(baseline, "embedding_analysis")
            current_attr_cache = repo.load(current, "attribute_analysis")
            current_emb_cache = repo.load(current, "embedding_analysis")

            if not baseline_attr_cache or not current_attr_cache:
                print("[yellow]⚠️ Repository cache missing for requested versions; drift may be incomplete.[/yellow]")

            drift_cfg.update({
                "baseline_attr_cache": baseline_attr_cache,
                "baseline_emb_cache": baseline_emb_cache,
                "current_attr_cache": current_attr_cache,
                "current_emb_cache": current_emb_cache,
            })
        except ImportError:
            print("[yellow]⚠️ Vision cache utilities not available; falling back to local caches.[/yellow]")
        except Exception as cache_err:
            print(f"[yellow]⚠️ Failed to load repository caches: {cache_err}[/yellow]")
        
        # Call vision plugin drift_detect
        try:
            res = get_pmgr().hook.drift_detect(
                ref_path=data_path,  # Dataset path where cache is located
                cur_path=data_path,  # Same for current
                detector="mmd",
                cfg=drift_cfg,
                output_path=output_path
            )
            print(_pretty(res))
        except Exception as e:
            print(f"[bold red]❌ Error:[/bold red] {e}")
            import traceback
            traceback.print_exc()
    
    else:
        # Cross-dataset drift
        print(f"[bold cyan]Cross-dataset drift analysis: {dataset1} vs {dataset2}[/bold cyan]")
        
        # Get dataset paths using new mapping system
        ds1_path = get_dataset_path(dataset1)
        ds2_path = get_dataset_path(dataset2)
        
        if not ds1_path:
            print(f"[bold red]❌ Dataset '{dataset1}' not found[/bold red]")
            return
        if not ds2_path:
            print(f"[bold red]❌ Dataset '{dataset2}' not found[/bold red]")
            return
        
        data_path1 = ds1_path
        data_path2 = ds2_path
        output_path = f"analysis/drift_compare_{dataset1}_vs_{dataset2}/"
        
        # Load drift config
        drift_cfg = params.get('drift', {})
        
        print(f"📊 Reference: {dataset1} ({data_path1})")
        print(f"📊 Current:   {dataset2} ({data_path2})")
        print(f"📊 Output:    {output_path}")
        print()
        
        # Call vision plugin drift_detect with different datasets
        try:
            res = get_pmgr().hook.drift_detect(
                ref_path=data_path1,  # First dataset path
                cur_path=data_path2,  # Second dataset path
                detector="mmd",
                cfg=drift_cfg,
                output_path=output_path
            )
            print(_pretty(res))
        except Exception as e:
            print(f"[bold red]❌ Error:[/bold red] {e}")
            import traceback
            traceback.print_exc()

# ============================================================================
# Experiment Commands (통합된 exp 커맨드)
# ============================================================================

@exp_app.command("run")
def exp_run_command(
    dataset: str = typer.Argument(..., help="Dataset name or name@version/alias (e.g., my_data@best_acc_sampled)"),
    plugin: str = typer.Option("yolo", "--plugin", "-p", help="Plugin name (yolo, vision, etc.)"),
    model: str = typer.Option("yolov8n.pt", "--model", "-m", help="YOLO model (yolov8n, yolov8s, etc.)"),
    epochs: int = typer.Option(100, "--epochs", "-e", help="Number of epochs"),
    batch: int = typer.Option(16, "--batch", "-b", help="Batch size"),
    imgsz: int = typer.Option(640, "--imgsz", "-i", help="Image size"),
    device: str = typer.Option("cpu", "--device", "-d", help="Device (cpu, 0, 1, etc.)"),
    data_yaml: Optional[str] = typer.Option(None, "--data", help="Path to data.yaml"),
    classes: List[str] = typer.Option([], "--class", "-c", help="Class names (repeatable)"),
    use_mlflow: bool = typer.Option(True, "--mlflow/--no-mlflow", help="Use MLflow tracking (default: True)"),
    use_dvc: bool = typer.Option(False, "--dvc", help="Use DVC experiments (requires Git, legacy mode)"),
    queue: bool = typer.Option(False, "--queue", help="Queue the experiment (DVC mode only)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run mode (DVC mode only)"),
):
    """
    Run a new experiment with auto-generated ID.
    
    Uses MLflow tracking by default (no Git required).
    Use --dvc flag for legacy DVC experiment mode (requires Git).
    
    Supports version/alias reference: dataset_name@version or dataset_name@alias
    
    Examples:
        ddoc exp run test_data                    # MLflow mode (default)
        ddoc exp run test_data@v1.0 --model yolov8s.pt --epochs 200
        ddoc exp run test_data --dvc              # DVC mode (requires Git)
        ddoc exp run test_data --no-mlflow        # Disable MLflow
    """
    # Auto-generate experiment ID
    exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"[bold cyan]🚀 Running Experiment: {exp_id}[/bold cyan]")
    
    # Parse dataset reference
    dataset_name, version_or_alias = _resolve_dataset_reference(dataset)
    
    # Check dataset version status
    try:
        from ddoc.core.version_service import get_version_service
        version_service = get_version_service()
        version_service.check_version_state(dataset_name)
        
        # Get current status
        status = version_service.get_dataset_status(dataset_name)
        
        # Resolve version/alias if provided
        if version_or_alias:
            # Try to resolve alias first
            resolved_version = version_service.get_dataset_version_by_alias(
                dataset_name, version_or_alias
            )
            if resolved_version:
                current_version = resolved_version
                print(f"📋 Resolved alias '{version_or_alias}' → {current_version}")
            else:
                # Assume it's a version tag
                current_version = version_or_alias
                print(f"📋 Using version: {current_version}")
        else:
            # Use current version
            current_version = status['current_version']
            print(f"📋 Current version: {current_version}")
        
    except Exception as e:
        print(f"[bold red]❌ Version check failed: {e}[/bold red]")
        return
    
    # Get dataset path using new mapping system
    dataset_path = get_dataset_path(dataset_name)
    
    if not dataset_path:
        print(f"[bold red]❌ Dataset not found: {dataset_name}[/bold red]")
        print("   Provide a valid path or register the dataset with 'ddoc dataset add'")
        return
    
    # Determine data.yaml path
    if data_yaml is None:
        data_yaml = str(dataset_path / "data.yaml")
    
    # Prepare parameters
    train_params = {
        'model': model,
        'epochs': epochs,
        'imgsz': imgsz,
        'batch': batch,
        'device': device,
        'exp_name': exp_id,
        'data_yaml': data_yaml,
        'classes': classes if classes else None
    }
    
    # Choose tracking mode
    if use_dvc:
        # Legacy DVC mode (requires Git)
        _run_dvc_experiment(
            exp_id=exp_id,
            dataset_name=dataset_name,
            dataset_path=dataset_path,
            current_version=current_version,
            plugin=plugin,
            train_params=train_params,
            queue=queue,
            dry_run=dry_run,
            version_service=version_service
        )
    elif use_mlflow:
        # MLflow mode (default, no Git required)
        _run_mlflow_experiment(
            exp_id=exp_id,
            dataset_name=dataset_name,
            dataset_path=dataset_path,
            current_version=current_version,
            model=model,
            plugin=plugin,
            train_params=train_params
        )
    else:
        print(f"[yellow]⚠️  No tracking mode selected. Use --mlflow or --dvc[/yellow]")
        return


def _run_mlflow_experiment(
    exp_id: str,
    dataset_name: str,
    dataset_path: Path,
    current_version: str,
    model: str,
    plugin: str,
    train_params: Dict[str, Any]
):
    """Run experiment with MLflow tracking"""
    try:
        from ddoc.core.mlflow_experiment_service import get_mlflow_experiment_service
        
        print(f"[cyan]📊 Using MLflow tracking[/cyan]")
        
        mlflow_service = get_mlflow_experiment_service()
        result = mlflow_service.run_experiment(
            dataset_name=dataset_name,
            dataset_version=current_version,
            model=model,
            params=train_params,
            plugin=plugin
        )
        
        if result['success']:
            print(f"\n[green]✅ Experiment completed successfully![/green]")
            print(f"[blue]📊 MLflow Run ID: {result['mlflow_run_id']}[/blue]")
            print(f"[blue]🔗 Dataset: {result['dataset_id']}[/blue]")
            print(f"[blue]📁 Results: {result['results_dir']}[/blue]")
            print(f"\n[cyan]💡 View in MLflow UI:[/cyan]")
            print(f"   cd {Path.cwd()}")
            print(f"   mlflow ui")
            
            # 메트릭 출력
            if result.get('metrics'):
                print(f"\n[cyan]📈 Metrics:[/cyan]")
                for k, v in result['metrics'].items():
                    print(f"   {k}: {v:.4f}")
        else:
            print(f"[red]❌ Experiment failed: {result.get('error')}[/red]")
            
    except ImportError:
        print(f"[red]❌ MLflow not installed. Install with: pip install mlflow[/red]")
    except Exception as e:
        print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()


def _run_dvc_experiment(
    exp_id: str,
    dataset_name: str,
    dataset_path: Path,
    current_version: str,
    plugin: str,
    train_params: Dict[str, Any],
    queue: bool,
    dry_run: bool,
    version_service
):
    """Run experiment with DVC (legacy mode)"""
    try:
        print(f"[cyan]📊 Using DVC experiments (legacy mode)[/cyan]")
        print(f"[yellow]⚠️  Note: DVC experiments require Git repository[/yellow]")
        # Create experiment metadata
        exp_metadata = get_experiment_service_instance().create_experiment_metadata(
            name=exp_id,
            dataset=dataset_name,
            plugin=plugin,
            params=train_params
        )
        
        # Create experiment version
        exp_version = version_service.create_experiment_version(
            dataset_name=dataset_name,
            dataset_version=current_version,
            exp_name=exp_id
        )
        
        # Run experiment via DVC
        if queue:
            res = get_experiment_service_instance().run_experiment(
                name=exp_id,
                params=train_params,
                queue=True,
                dry_run=dry_run
            )
        else:
            res = get_experiment_service_instance().run_experiment(
                name=exp_id,
                params=train_params,
                queue=False,
                dry_run=dry_run
            )
        
        if res.get('success'):
            # Train via plugin if not dry run
            if not dry_run:
                if plugin == "yolo":
                    plugin_res = get_pmgr().hook.retrain_run(
                        train_path=dataset_path,
                        trainer="yolo",
                        params=train_params,
                        model_out="experiments"
                    )
                else:
                    plugin_res = get_pmgr().hook.retrain_run(
                        train_path=dataset_path,
                        trainer=plugin,
                        params=train_params,
                        model_out="experiments"
                    )
                
                # Handle plugin results
                if isinstance(plugin_res, list):
                    plugin_res = next((r for r in plugin_res if r and r.get('status') != 'error'), None)
                
                if plugin_res and plugin_res.get('status') != 'error':
                    # Save experiment results
                    metrics = plugin_res.get('metrics', {})
                    get_experiment_service_instance().save_experiment_results(exp_metadata['experiment_id'], metrics)
                    
                    # Add experiment to lineage with version info
                    experiment_id = f"{exp_id}@{exp_version}"
                    experiment_name = f"{exp_id}@{exp_version}"
                    dataset_id = f"{dataset_name}@{current_version}"
                    
                    get_metadata_service_instance().add_experiment(
                        experiment_id=experiment_id,
                        experiment_name=experiment_name,
                        dataset_id=dataset_id,
                        metadata={
                            "plugin": plugin,
                            "metrics": metrics,
                            "params": train_params,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    print(f"✅ Experiment linked to dataset version {current_version}")
                    print(_pretty(plugin_res))
                else:
                    print(f"[bold red]❌ Plugin execution failed[/bold red]")
                    if plugin_res:
                        print(_pretty(plugin_res))
            
            print(_pretty(res))
        else:
            print(f"[bold red]❌ Experiment failed:[/bold red] {res.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()


@exp_app.command("list")
def exp_list_command(
    dataset: Optional[str] = typer.Option(None, "--dataset", "-d", help="Filter by dataset"),
    plugin: Optional[str] = typer.Option(None, "--plugin", "-p", help="Filter by plugin"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of experiments to show")
):
    """
    List experiments.
    
    Examples:
        ddoc exp list
        ddoc exp list --dataset test_data
        ddoc exp list --plugin yolo --status completed
    """
    print(f"[bold cyan]🔬 Experiment List[/bold cyan]")
    
    try:
        # 실험 목록 조회
        experiments = get_experiment_service_instance().list_experiments(dataset)
        
        if not experiments:
            print("[yellow]No experiments found.[/yellow]")
            return
        
        # 제한 적용
        experiments = experiments[:limit]
        
        # 테이블 형태로 출력
        print(f"\n[bold]Found {len(experiments)} experiments:[/bold]")
        print("-" * 80)
        print(f"{'ID':<20} {'Dataset':<15} {'Plugin':<10} {'Status':<10} {'Start Time':<20}")
        print("-" * 80)
        
        for exp in experiments:
            exp_id = exp.get('name', exp.get('experiment_id', 'Unknown'))
            dataset = exp.get('dataset_name', 'Unknown')
            plugin = exp.get('plugin', 'yolo')
            status = exp.get('status', 'completed')
            start_time = exp.get('timestamp', 'Unknown')
            
            # Format timestamp if it's a string
            if isinstance(start_time, str) and 'T' in start_time:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    start_time = str(start_time)[:19]  # Truncate if parsing fails
            
            print(f"{exp_id:<20} {dataset:<15} {plugin:<10} {status:<10} {start_time:<20}")
        
        print("-" * 80)
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")


@exp_app.command("show")
def exp_show_command(
    experiment_id: str = typer.Argument(..., help="Experiment ID")
):
    """
    Show detailed information for a specific experiment.
    
    Examples:
        ddoc exp show exp_20241021_143022
    """
    print(f"[bold cyan]🔍 Experiment Details: {experiment_id}[/bold cyan]")
    
    try:
        # 실험 조회
        experiment = get_experiment_service_instance().get_experiment(experiment_id)
        
        if not experiment:
            print(f"[red]❌ Experiment '{experiment_id}' not found.[/red]")
            return
        
        # 상세 정보 출력
        print(f"\n[bold]Basic Information:[/bold]")
        print(f"  ID: {experiment.get('name', experiment.get('experiment_id', 'Unknown'))}")
        print(f"  Dataset: {experiment.get('dataset_name', 'Unknown')}")
        print(f"  Plugin: {experiment.get('plugin', 'yolo')}")
        print(f"  Status: {experiment.get('status', 'completed')}")
        print(f"  Start Time: {experiment.get('timestamp', 'Unknown')}")
        
        # Output directory
        output_dir = experiment.get('output_dir', '')
        if output_dir:
            print(f"  Output Directory: {output_dir}")
        
        # 파라미터 정보
        params = experiment.get('params', {})
        if params:
            print(f"\n[bold]Parameters:[/bold]")
            for key, value in params.items():
                print(f"  {key}: {value}")
        
        # 메트릭 정보
        metrics = experiment.get('metrics', {})
        if metrics:
            print(f"\n[bold]Metrics:[/bold]")
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
        
        # 로그 정보 (현재는 없음)
        logs = experiment.get('logs', [])
        if logs:
            print(f"\n[bold]Logs:[/bold]")
            for log in logs[-5:]:  # 최근 5개 로그만 표시
                print(f"  {log}")
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")


@exp_app.command("compare")
def exp_compare_command(
    experiment_ids: List[str] = typer.Argument(..., help="Experiment IDs to compare"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for comparison report"),
    use_mlflow: bool = typer.Option(False, "--mlflow", help="Use MLflow data for comparison")
):
    """
    Compare multiple experiments.
    
    Supports both legacy (DVC) and MLflow experiments.
    
    Examples:
        ddoc exp compare exp1 exp2 exp3
        ddoc exp compare exp1 exp2 --mlflow
        ddoc exp compare exp1 exp2 --output comparison.json
    """
    print(f"[bold cyan]📊 Experiment Comparison[/bold cyan]")
    
    if len(experiment_ids) < 2:
        print("[red]❌ At least 2 experiments are required for comparison.[/red]")
        return
    
    try:
        if use_mlflow:
            # MLflow 비교
            from ddoc.core.mlflow_experiment_service import get_mlflow_experiment_service
            mlflow_service = get_mlflow_experiment_service()
            comparison = mlflow_service.compare_experiments(experiment_ids)
        else:
            # 기존 DVC 비교
            comparison = get_experiment_service_instance().compare_experiments(experiment_ids)
        
        print(f"\n[bold]Comparing {len(experiment_ids)} experiments:[/bold]")
        print(f"  Experiments: {', '.join(experiment_ids)}")
        
        # 요약 정보
        experiments = comparison['experiments']
        print(f"\n[bold]Summary:[/bold]")
        print(f"  Total Experiments: {len(experiments)}")
        
        datasets = set(exp.get('dataset_name', 'Unknown') for exp in experiments)
        plugins = set(exp.get('plugin', 'yolo') for exp in experiments)
        statuses = set(exp.get('status', 'completed') for exp in experiments)
        
        print(f"  Datasets: {', '.join(datasets)}")
        print(f"  Plugins: {', '.join(plugins)}")
        print(f"  Status: {', '.join(statuses)}")
        
        # 메트릭 비교
        if comparison['metrics_comparison']:
            print(f"\n[bold]Metrics Comparison:[/bold]")
            for metric, values in comparison['metrics_comparison'].items():
                print(f"\n  {metric}:")
                for exp_id, value in values.items():
                    print(f"    {exp_id}: {value:.4f}")
        
        # 파라미터 비교 (간단한 버전)
        print(f"\n[bold]Parameters Comparison:[/bold]")
        for i, exp in enumerate(experiments):
            exp_id = exp.get('name', exp.get('experiment_id', f'exp_{i}'))
            print(f"\n  {exp_id}:")
            # 주요 파라미터만 표시
            params = exp.get('params', {})
            key_params = ['model', 'epochs', 'batch', 'device', 'imgsz']
            for param in key_params:
                if param in params:
                    print(f"    {param}: {params[param]}")
        
        # 결과 저장
        if output:
            with open(output, 'w') as f:
                json.dump(comparison, f, indent=2, default=str)
            print(f"\n[green]✅ Comparison report saved to: {output}[/green]")
        
    except Exception as e:
        print(f"[red]❌ Error comparing experiments: {e}[/red]")


@exp_app.command("status")
def exp_status_command(
    experiment_id: Optional[str] = typer.Option(None, "--id", "-i", help="Specific experiment ID"),
    all: bool = typer.Option(False, "--all", "-a", help="Show status of all experiments")
):
    """
    Show experiment status.
    
    Examples:
        ddoc exp status --id exp_20241021_143022
        ddoc exp status --all
    """
    print(f"[bold cyan]📊 Experiment Status[/bold cyan]")
    
    try:
        if experiment_id:
            # 특정 실험 상태
            experiment = get_experiment_service_instance().get_experiment(experiment_id)
            if experiment:
                status = experiment.get('status', 'unknown')
                print(f"Experiment {experiment_id}: {status}")
            else:
                print(f"[red]❌ Experiment '{experiment_id}' not found.[/red]")
        elif all:
            # 모든 실험 상태
            experiments = get_experiment_service_instance().list_experiments()
            print(f"\n[bold]All Experiments Status:[/bold]")
            print("-" * 60)
            print(f"{'ID':<25} {'Dataset':<15} {'Status':<10}")
            print("-" * 60)
            
            for exp in experiments:
                exp_id = exp.get('name', exp.get('experiment_id', 'Unknown'))
                dataset = exp.get('dataset_name', 'Unknown')
                status = exp.get('status', 'unknown')
                print(f"{exp_id:<25} {dataset:<15} {status:<10}")
            
            print("-" * 60)
        else:
            print("[yellow]Please specify --id or --all option.[/yellow]")
    except Exception as e:
        print(f"[bold red]❌ Error:[/bold red] {e}")


@exp_app.command("best")
def exp_best_command(
    dataset: str = typer.Argument(..., help="Dataset name@version (e.g., source@v1.0)"),
    metric: str = typer.Option("mAP50-95", "--metric", "-m", help="Metric to compare (default: mAP50-95)"),
):
    """
    Find best experiment for a dataset version based on a metric.
    
    Only works with MLflow-tracked experiments.
    
    Examples:
        ddoc exp best source@v1.0
        ddoc exp best source@v1.0 --metric mAP50
        ddoc exp best target@v2.1 --metric precision
    """
    try:
        from ddoc.core.mlflow_experiment_service import get_mlflow_experiment_service
        
        # Parse dataset reference
        if '@' not in dataset:
            print(f"[red]❌ Please specify dataset version (e.g., {dataset}@v1.0)[/red]")
            return
        
        dataset_name, version = dataset.split('@', 1)
        
        print(f"[cyan]🏆 Finding best experiment for {dataset}[/cyan]")
        print(f"[cyan]   Metric: {metric}[/cyan]\n")
        
        mlflow_service = get_mlflow_experiment_service()
        best = mlflow_service.get_best_experiment_for_dataset(
            dataset_name=dataset_name,
            dataset_version=version,
            metric=f"metrics.{metric}"
        )
        
        if best:
            exp_id = best.get('tags.ddoc.experiment_id', 'Unknown')
            metric_value = best.get(f'metrics.{metric}', 'N/A')
            run_id = best.get('run_id', 'Unknown')
            start_time = best.get('start_time', 'Unknown')
            
            print(f"[green]✅ Best experiment found:[/green]\n")
            print(f"  Experiment ID: {exp_id}")
            print(f"  MLflow Run ID: {run_id}")
            print(f"  {metric}: {metric_value}")
            print(f"  Started: {start_time}")
            
            # Show other metrics if available
            print(f"\n[cyan]Other metrics:[/cyan]")
            for col in best.keys():
                if col.startswith('metrics.') and col != f'metrics.{metric}':
                    metric_name = col.replace('metrics.', '')
                    value = best.get(col)
                    if value is not None:
                        print(f"  {metric_name}: {value}")
        else:
            print(f"[yellow]No experiments found for {dataset}[/yellow]")
            print(f"[yellow]Make sure experiments were run with --mlflow flag[/yellow]")
    
    except ImportError:
        print(f"[red]❌ MLflow not installed. Install with: pip install mlflow[/red]")
    except Exception as e:
        print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()


# ============================================================================
# Plugin Commands (플러그인 관리)
# ============================================================================

@plugin_app.command("list")
def plugin_list_command():
    """
    List all loaded plugins.
    """
    print("[bold cyan]🔌 Loaded Plugins:[/bold cyan]")

    # Get plugin manager
    pmgr = get_pmgr()
    
    # Get all registered plugins
    plugins = []
    for name, plugin in pmgr.list_plugins().items():
        # Check if plugin has hook attribute (for class-based plugins)
        try:
            hooks_count = len(plugin.hook.get_hookimpls()) if hasattr(plugin, 'hook') else 0
        except:
            hooks_count = 0
            
        plugins.append({
            'name': name,
            'plugin': plugin,
            'hooks': hooks_count
        })
    
    if plugins:
        print(f"\n[bold]Found {len(plugins)} plugins:[/bold]")
        print("-" * 60)
        print(f"{'Name':<20} {'Hooks':<10} {'Status':<10}")
        print("-" * 60)
        
        for plugin_info in plugins:
            name = plugin_info['name']
            hooks = plugin_info['hooks']
            status = "active"  # Assume active if loaded
            
            print(f"{name:<20} {hooks:<10} {status:<10}")
        
        print("-" * 60)
    else:
        print("  No plugins loaded.")


@plugin_app.command("info")
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

# ============================================================================
# Visualization Commands
# ============================================================================

def vis():
    """
    Run GUI app
    """
    meta = get_pmgr().hook.vis_run()

    # 메인 앱에서 실행하는 구조
    '''
    for item in meta:
        if item.get("type") == "streamlit":
            app_path = item.get("app_path")
            if app_path:
                subprocess.Popen(["streamlit", "run", app_path])
    '''

# ============================================================================
# Lineage Commands (기존 유지)
# ============================================================================

@lineage_app.command("show")
def lineage_show_command(
    node_id: str = typer.Argument(..., help="Node ID to show lineage for"),
    depth: int = typer.Option(2, "--depth", "-d", help="Depth of lineage to show")
):
    """
    Show lineage information for a specific node.
    
    Examples:
        ddoc lineage show test_yolo
        ddoc lineage show test_yolo --depth 3
    """
    print(f"[bold cyan]🔗 Lineage for: {node_id}[/bold cyan]")
    
    try:
        lineage = get_metadata_service_instance().get_lineage(node_id, depth)
        
        if "error" in lineage:
            print(f"[red]❌ {lineage['error']}[/red]")
            return
        
        print(f"\n[bold]Lineage Summary:[/bold]")
        print(f"  Root Node: {lineage['root_node']}")
        print(f"  Depth: {lineage['depth']}")
        print(f"  Total Nodes: {lineage['total_nodes']}")
        print(f"  Total Edges: {lineage['total_edges']}")
        
        # 노드 정보
        if lineage['nodes']:
            print(f"\n[bold]Nodes:[/bold]")
            for node in lineage['nodes']:
                node_type = node['type']
                node_name = node['name']
                timestamp = node['timestamp']
                print(f"  [{node_type}] {node_name} ({node['id']}) - {timestamp}")
        
        # 엣지 정보
        if lineage['edges']:
            print(f"\n[bold]Relationships:[/bold]")
            for edge in lineage['edges']:
                relationship = edge['relationship']
                source = edge['source']
                target = edge['target']
                print(f"  {source} --[{relationship}]--> {target}")
        
    except Exception as e:
        print(f"[red]❌ Error showing lineage: {e}[/red]")


@lineage_app.command("graph")
def lineage_graph_command(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for graph visualization"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, dot")
):
    """
    Generate full lineage graph.
    
    Examples:
        ddoc lineage graph
        ddoc lineage graph --output lineage.dot --format dot
    """
    print(f"[bold cyan]📊 Full Lineage Graph[/bold cyan]")
    
    try:
        full_lineage = get_metadata_service_instance().get_full_lineage()
        
        print(f"\n[bold]Graph Summary:[/bold]")
        print(f"  Total Nodes: {full_lineage['total_nodes']}")
        print(f"  Total Edges: {full_lineage['total_edges']}")
        print(f"  Node Types: {', '.join(full_lineage['node_types'])}")
        print(f"  Relationship Types: {', '.join(full_lineage['relationship_types'])}")
        
        # 노드 타입별 통계
        node_type_counts = {}
        for node in full_lineage['nodes']:
            node_type = node['type']
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
        
        print(f"\n[bold]Node Type Distribution:[/bold]")
        for node_type, count in node_type_counts.items():
            print(f"  {node_type}: {count}")
        
        # 관계 타입별 통계
        relationship_counts = {}
        for edge in full_lineage['edges']:
            rel_type = edge['relationship']
            relationship_counts[rel_type] = relationship_counts.get(rel_type, 0) + 1
        
        print(f"\n[bold]Relationship Distribution:[/bold]")
        for rel_type, count in relationship_counts.items():
            print(f"  {rel_type}: {count}")
        
        # 출력 파일 저장
        if output:
            if format == "dot":
                # DOT 형식으로 저장 (Graphviz용)
                dot_content = get_metadata_service_instance()._generate_dot_format()
                with open(output, 'w') as f:
                    f.write(dot_content)
                print(f"\n[green]✅ Graph saved to: {output}[/green]")
            else:
                # JSON 형식으로 저장
                with open(output, 'w') as f:
                    json.dump(full_lineage, f, indent=2)
                print(f"\n[green]✅ Graph saved to: {output}[/green]")
        
    except Exception as e:
        print(f"[red]❌ Error generating graph: {e}[/red]")


@lineage_app.command("overview")
def lineage_overview_command():
    """
    Show overview of all datasets and their lineage relationships.
    
    Examples:
        ddoc lineage overview
    """
    print(f"[bold cyan]📊 Dataset Lineage Overview[/bold cyan]")
    
    try:
        overview = get_metadata_service_instance().get_lineage_overview()
        
        # 전체 통계
        print(f"\n[bold]Summary:[/bold]")
        print(f"  Total Nodes: {overview['total_nodes']}")
        print(f"  Total Relationships: {overview['total_edges']}")
        print(f"  Datasets: {len(overview['datasets'])}")
        print(f"  Analytics: {len(overview['analyses'])}")
        print(f"  Experiments: {len(overview['experiments'])}")
        print(f"  Drift Analytics: {len(overview['drift_analyses'])}")
        print("\n[dim]ℹ️  자세한 순서는 'ddoc dataset timeline <dataset>' 명령으로 확인할 수 있습니다.[/dim]")
        
        # 데이터셋별 트리 구조 출력 (데이터셋 이름으로 그룹화)
        if overview['datasets']:
            print(f"\n[bold]📦 Dataset Lineage Tree:[/bold]")
            
            # 데이터셋 이름별로 그룹화
            dataset_groups = {}
            for dataset in overview['datasets']:
                dataset_id = dataset['id']
                dataset_name = dataset['name']
                # dataset_id가 "name@version" 형식이면 이름 추출, 아니면 원본 사용
                if '@' in dataset_id:
                    base_name = dataset_id.split('@')[0]
                    version = dataset_id.split('@')[1] if '@' in dataset_id else ''
                else:
                    base_name = dataset_name
                    version = dataset.get('version', '')
                
                if base_name not in dataset_groups:
                    dataset_groups[base_name] = []
                
                children = overview['dataset_children'].get(dataset_id, {})
                dataset_groups[base_name].append({
                    'id': dataset_id,
                    'name': dataset_name,
                    'version': version,
                    'children': children
                })
            
            # 그룹화된 데이터셋 출력
            dataset_names = sorted(dataset_groups.keys())
            for ds_idx, base_name in enumerate(dataset_names):
                versions = sorted(dataset_groups[base_name], key=lambda x: x['version'])
                
                # 데이터셋 이름 출력 (마지막 데이터셋이면 └──, 아니면 ├──)
                if ds_idx == len(dataset_names) - 1:
                    print(f"[green]└── 📦 {base_name}[/green]")
                    ds_prefix = "    "
                    last_prefix = "    "
                else:
                    print(f"[green]├── 📦 {base_name}[/green]")
                    ds_prefix = "│   "
                    last_prefix = "│   "
                
                # 각 버전별 출력
                for v_idx, version_data in enumerate(versions):
                    version = version_data['version']
                    version_id = version_data['id']
                    children = version_data['children']
                    
                    # 버전 헤더 (마지막 버전이면 └──, 아니면 ├──)
                    if v_idx == len(versions) - 1:
                        print(f"{ds_prefix}[cyan]└── v{version}[/cyan] [dim]({version_id})[/dim]")
                        version_prefix = last_prefix + "    "
                    else:
                        print(f"{ds_prefix}[cyan]├── v{version}[/cyan] [dim]({version_id})[/dim]")
                        version_prefix = ds_prefix + "│   "
                    
                    # 하위 노드들 출력 (분석, 실험, 드리프트 분석)
                    all_children_items = []
                    all_children_items.extend([('analysis', a) for a in children.get('analyses', [])])
                    all_children_items.extend([('experiment', e) for e in children.get('experiments', [])])
                    all_children_items.extend([('drift', d) for d in children.get('drift_analyses', [])])
                    
                    for c_idx, (child_type, child) in enumerate(all_children_items):
                        child_name = child['name']
                        child_id = child['id']
                        
                        # 아이콘 선택
                        if child_type == 'analysis':
                            icon = "📈"
                        elif child_type == 'experiment':
                            icon = "🧪"
                        else:  # drift
                            icon = "📊"
                        
                        # 마지막 항목이면 └──, 아니면 ├──
                        if c_idx == len(all_children_items) - 1:
                            print(f"{version_prefix}[green]└── {icon} {child_name}[/green] [dim]({child_id})[/dim]")
                        else:
                            print(f"{version_prefix}[green]├── {icon} {child_name}[/green] [dim]({child_id})[/dim]")
                
                # 데이터셋 간 구분 (마지막 데이터셋이 아닐 때)
                if ds_idx < len(dataset_names) - 1:
                    print()
        
        # 관계 타입별 통계
        if overview['relationships']:
            print(f"\n[bold]🔗 Relationship Types:[/bold]")
            rel_counts = {}
            for rel in overview['relationships']:
                rel_type = rel['relationship']
                rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
            
            for rel_type, count in rel_counts.items():
                print(f"  {rel_type}: {count}")
        
        # 독립적인 노드들 (관계가 없는 노드들)
        independent_nodes = []
        connected_nodes = set()
        for rel in overview['relationships']:
            connected_nodes.add(rel['source'])
            connected_nodes.add(rel['target'])
        
        for node_type, nodes in [
            ('datasets', overview['datasets']),
            ('analyses', overview['analyses']),
            ('experiments', overview['experiments']),
            ('drift_analyses', overview['drift_analyses'])
        ]:
            for node in nodes:
                if node['id'] not in connected_nodes:
                    independent_nodes.append(node)
        
        if independent_nodes:
            print(f"\n[bold]🔸 Independent Nodes:[/bold]")
            for node in independent_nodes:
                node_type = node.get('type', 'unknown')
                node_name = node['name']
                node_id = node['id']
                icon = {'dataset': '📦', 'analysis': '📈', 'experiment': '🧪', 'drift_analysis': '📊'}.get(node_type, '❓')
                print(f"  {icon} {node_name} [dim]({node_id})[/dim]")
        
    except Exception as e:
        print(f"[red]❌ Error showing overview: {e}[/red]")


@lineage_app.command("impact")
def lineage_impact_command(
    node_id: str = typer.Argument(..., help="Node ID to analyze impact for")
):
    """
    Analyze impact of changes to a specific node.
    
    Examples:
        ddoc lineage impact test_yolo
        ddoc lineage impact exp_ref
    """
    print(f"[bold cyan]⚡ Impact Analysis for: {node_id}[/bold cyan]")
    
    try:
        impact = get_metadata_service_instance().get_impact_analysis(node_id)
        
        if "error" in impact:
            print(f"[red]❌ {impact['error']}[/red]")
            return
        
        print(f"\n[bold]Impact Analysis:[/bold]")
        print(f"  Node: {impact['node_id']}")
        print(f"  Impact Count: {impact['impact_count']}")
        print(f"  Impact Severity: {impact['impact_severity']}")
        
        # 직접 의존 노드들
        if impact['direct_dependents']:
            print(f"\n[bold]Direct Dependents ({len(impact['direct_dependents'])}):[/bold]")
            for dependent in impact['direct_dependents']:
                print(f"  - {dependent}")
        
        # 모든 의존 노드들
        if impact['all_dependents']:
            print(f"\n[bold]All Dependents ({len(impact['all_dependents'])}):[/bold]")
            for dependent in impact['all_dependents']:
                print(f"  - {dependent}")
        
        # 영향도에 따른 권장사항
        severity = impact['impact_severity']
        if severity == 'high':
            print(f"\n[yellow]⚠️  High Impact Warning:[/yellow]")
            print(f"  Changing this node will affect {impact['impact_count']} other nodes.")
            print(f"  Consider creating a backup or testing in a separate environment.")
        elif severity == 'medium':
            print(f"\n[yellow]⚠️  Medium Impact:[/yellow]")
            print(f"  Changing this node will affect {impact['impact_count']} other nodes.")
            print(f"  Review dependencies before making changes.")
        else:
            print(f"\n[green]✅ Low Impact:[/green]")
            print(f"  Changing this node will have minimal impact.")
        
    except Exception as e:
        print(f"[red]❌ Error analyzing impact: {e}[/red]")


@lineage_app.command("dependencies")
def lineage_dependencies_command(
    node_id: str = typer.Argument(..., help="Node ID to show dependencies for")
):
    """
    Show dependencies for a specific node.
    
    Examples:
        ddoc lineage dependencies test_yolo
        ddoc lineage dependencies exp_ref
    """
    print(f"[bold cyan]🔗 Dependencies for: {node_id}[/bold cyan]")
    
    try:
        dependencies = get_metadata_service_instance().get_dependencies(node_id)
        
        if not dependencies:
            print(f"[yellow]No dependencies found for {node_id}[/yellow]")
            return
        
        print(f"\n[bold]Dependencies ({len(dependencies)}):[/bold]")
        for dep in dependencies:
            # 노드 정보 가져오기
            if dep in metadata_service.graph:
                node_info = metadata_service.graph.nodes[dep]
                node_type = node_info.get('type', 'unknown')
                node_name = node_info.get('name', dep)
                print(f"  [{node_type}] {node_name} ({dep})")
            else:
                print(f"  - {dep}")
        
    except Exception as e:
        print(f"[red]❌ Error getting dependencies: {e}[/red]")


@lineage_app.command("dependents")
def lineage_dependents_command(
    node_id: str = typer.Argument(..., help="Node ID to show dependents for")
):
    """
    Show dependents for a specific node.
    
    Examples:
        ddoc lineage dependents test_yolo
        ddoc lineage dependents exp_ref
    """
    print(f"[bold cyan]🔗 Dependents for: {node_id}[/bold cyan]")
    
    try:
        dependents = get_metadata_service_instance().get_dependents(node_id)
        
        if not dependents:
            print(f"[yellow]No dependents found for {node_id}[/yellow]")
            return
        
        print(f"\n[bold]Dependents ({len(dependents)}):[/bold]")
        for dep in dependents:
            # 노드 정보 가져오기
            if dep in metadata_service.graph:
                node_info = metadata_service.graph.nodes[dep]
                node_type = node_info.get('type', 'unknown')
                node_name = node_info.get('name', dep)
                print(f"  [{node_type}] {node_name} ({dep})")
            else:
                print(f"  - {dep}")
        
    except Exception as e:
        print(f"[red]❌ Error getting dependents: {e}[/red]")

# ============================================================================
# Register Function (메인 앱 연결)
# ============================================================================

# ============================================================================
# 환경 변수 기반 프롬프트 시스템 (virtualenv 방식)
# ============================================================================


# ============================================================================
# NEW COMMANDS: Init, Add, Commit, Checkout, etc. (v2.0)
# ============================================================================

def init(
    project_path: str = typer.Argument(".", help="Project directory path"),
    force: bool = typer.Option(False, "--force", "-f", help="Force initialization even if directory exists"),
):
    """
    Initialize a new ddoc workspace with scaffolding.
    
    Creates the complete project structure including data/, code/, notebooks/,
    experiments/ directories, and initializes both Git and DVC.
    
    Examples:
        ddoc init myproject      # Create new project
        ddoc init .              # Initialize current directory
        ddoc init sandbox/v4     # Create project in specific path
    """
    from ddoc.core.workspace import get_workspace_service
    
    print(f"[bold cyan]🚀 Initializing ddoc workspace...[/bold cyan]\n")
    
    workspace_service = get_workspace_service()
    result = workspace_service.init_workspace(project_path, force=force)
    
    if not result["success"]:
        print(f"[red]❌ Initialization failed: {result['error']}[/red]")
        raise typer.Exit(code=1)
    
    # Print success info
    print(f"[green]✅ Workspace created at: {result['project_path']}[/green]\n")
    print("[bold]Created structure:[/bold]")
    for dir_name in result["created_directories"]:
        print(f"  📁 {dir_name}")
    
    print(f"\n[bold]Created files:[/bold]")
    for file_name in result["files_created"]:
        print(f"  📄 {file_name}")
    
    # Print git/dvc status
    if result["git_initialized"]:
        print(f"\n[green]✅ Git initialized[/green]")
    else:
        print(f"\n[yellow]⚠️  Git not initialized. Please install git.[/yellow]")
    
    if result["dvc_initialized"]:
        print(f"[green]✅ DVC initialized[/green]")
    else:
        print(f"[yellow]⚠️  DVC not initialized. Please install dvc: pip install dvc[/yellow]")
    
    print(f"\n[bold cyan]Next steps:[/bold cyan]")
    print(f"  1. cd {result['project_path']}")
    print(f"  2. ddoc add --data /path/to/dataset")
    print(f"  3. ddoc add --code /path/to/train.py")
    print(f"  4. ddoc commit -m \"Initial baseline\" -a baseline")
    print()


def add(
    data: Optional[str] = typer.Option(None, "--data", help="Add data file or directory"),
    code: Optional[str] = typer.Option(None, "--code", help="Add code file"),
    notebook: Optional[str] = typer.Option(None, "--notebook", help="Add notebook file"),
):
    """
    Add files to the ddoc workspace (data/code/notebook).
    
    Automatically handles file copying, DVC tracking for data, and Git tracking for code.
    Supports zip/tar.gz extraction for data files.
    
    Examples:
        ddoc add --data datasets/train.zip
        ddoc add --data datasets/raw_images/
        ddoc add --code scripts/train.py
        ddoc add --notebook analysis.ipynb
    """
    from ddoc.core.file_service import get_file_service
    
    if not any([data, code, notebook]):
        print("[red]❌ Please specify at least one of: --data, --code, or --notebook[/red]")
        raise typer.Exit(code=1)
    
    file_service = get_file_service()
    
    # Add data
    if data:
        print(f"[cyan]📦 Adding data from: {data}[/cyan]")
        result = file_service.add_data(data)
        
        if result["success"]:
            print(f"[green]✅ Data added successfully[/green]")
            for item in result["added_items"]:
                print(f"   📁 {item}")
            
            if result.get("dvc_tracked"):
                print(f"[green]✅ DVC tracking enabled[/green]")
            if result.get("git_staged"):
                print(f"[green]✅ data.dvc staged in git[/green]")
        else:
            print(f"[red]❌ Failed to add data: {result['error']}[/red]")
            raise typer.Exit(code=1)
    
    # Add code
    if code:
        print(f"[cyan]💻 Adding code from: {code}[/cyan]")
        result = file_service.add_code(code)
        
        if result["success"]:
            print(f"[green]✅ Code added: {result['added_file']}[/green]")
            if result.get("git_staged"):
                print(f"[green]✅ Code staged in git[/green]")
        else:
            print(f"[red]❌ Failed to add code: {result['error']}[/red]")
            raise typer.Exit(code=1)
    
    # Add notebook
    if notebook:
        print(f"[cyan]📓 Adding notebook from: {notebook}[/cyan]")
        result = file_service.add_notebook(notebook)
        
        if result["success"]:
            print(f"[green]✅ Notebook added: {result['added_file']}[/green]")
            if result.get("git_staged"):
                print(f"[green]✅ Notebook staged in git[/green]")
        else:
            print(f"[red]❌ Failed to add notebook: {result['error']}[/red]")
            raise typer.Exit(code=1)
    
    print()


def snapshot(
    # Position argument (for show/restore)
    version: Optional[str] = typer.Argument(None, help="Snapshot version or alias (for show/restore)"),
    
    # Create snapshot
    message: Optional[str] = typer.Option(None, "-m", "--message", help="Create snapshot with message"),
    alias: Optional[str] = typer.Option(None, "-a", "--alias", help="Alias for new snapshot or set alias"),
    no_auto_commit: bool = typer.Option(False, "--no-auto-commit", help="Disable automatic git/dvc commit"),
    
    # List/View operations
    list_snapshots: bool = typer.Option(False, "-l", "--list", help="List all snapshots"),
    oneline: bool = typer.Option(False, "--oneline", help="Show compact one-line format"),
    limit: Optional[int] = typer.Option(None, "-n", "--limit", help="Limit number of snapshots shown"),
    
    # Restore operation
    restore: Optional[str] = typer.Option(None, "-r", "--restore", help="Restore snapshot"),
    
    # Compare operation
    diff: Optional[List[str]] = typer.Option(None, "--diff", help="Compare two snapshots (provide 2 versions)"),
    
    # Graph/lineage operation
    graph: bool = typer.Option(False, "--graph", help="Show snapshot lineage graph"),
    
    # Delete operation
    delete: Optional[str] = typer.Option(None, "--delete", help="Delete snapshot"),
    
    # Alias management
    set_alias: Optional[List[str]] = typer.Option(None, "--set-alias", help="Set alias (version alias)"),
    unalias: Optional[str] = typer.Option(None, "--unalias", help="Remove alias"),
    show_aliases: bool = typer.Option(False, "--show-aliases", help="Show all aliases"),
    
    # Edit operation
    rename: Optional[str] = typer.Option(None, "--rename", help="Rename snapshot description"),
    
    # Verify operations
    verify: Optional[str] = typer.Option(None, "--verify", help="Verify snapshot integrity"),
    verify_all: bool = typer.Option(False, "--verify-all", help="Verify all snapshots"),
    
    # Prune operation
    prune: bool = typer.Option(False, "--prune", help="Identify orphaned snapshots"),
    
    # Common flags
    force: bool = typer.Option(False, "-f", "--force", help="Force operation"),
):
    """
    Unified snapshot management command.
    
    # CREATE
    ddoc snapshot -m "baseline model" -a baseline
    
    # LIST (default action)
    ddoc snapshot
    ddoc snapshot --list
    ddoc snapshot --oneline
    
    # SHOW DETAILS
    ddoc snapshot v01
    ddoc snapshot baseline
    
    # RESTORE
    ddoc snapshot --restore v01
    ddoc snapshot -r baseline
    ddoc snapshot -r v01 --force
    
    # COMPARE
    ddoc snapshot --diff v01 v02
    ddoc snapshot --diff baseline production
    
    # GRAPH/LINEAGE
    ddoc snapshot --graph
    
    # DELETE
    ddoc snapshot --delete v01
    ddoc snapshot --delete baseline --force
    
    # ALIAS MANAGEMENT
    ddoc snapshot --set-alias v01 baseline
    ddoc snapshot --unalias baseline
    ddoc snapshot --show-aliases
    
    # EDIT
    ddoc snapshot --rename v01 "new description"
    
    # VERIFY
    ddoc snapshot --verify v01
    ddoc snapshot --verify-all
    
    # PRUNE
    ddoc snapshot --prune
    """
    from ddoc.core.snapshot_service import get_snapshot_service
    from ddoc.core.git_service import get_git_service
    
    snapshot_service = get_snapshot_service()
    
    # ========================================================================
    # CREATE SNAPSHOT
    # ========================================================================
    if message:
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
        return
    
    # ========================================================================
    # RESTORE SNAPSHOT
    # ========================================================================
    if restore:
        print(f"[cyan]🔄 Restoring snapshot: {restore}[/cyan]\n")
        result = snapshot_service.restore_snapshot(restore, force=force)
        
        if not result["success"]:
            print(f"[red]❌ Snapshot restore failed: {result['error']}[/red]")
            raise typer.Exit(code=1)
        
        print(f"[green]✅ Snapshot restored successfully![/green]\n")
        print(f"[bold]Snapshot ID:[/bold] {result['snapshot_id']}")
        if result.get("alias"):
            print(f"[bold]Alias:[/bold] {result['alias']}")
        print(f"[bold]Description:[/bold] {result['description']}")
        print()
        return
    
    # ========================================================================
    # COMPARE SNAPSHOTS
    # ========================================================================
    if diff and len(diff) >= 2:
        version1, version2 = diff[0], diff[1]
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
    if rename and version:
        result = snapshot_service.edit_description(version, rename)
        
        if not result["success"]:
            print(f"[red]❌ Edit failed: {result['error']}[/red]")
            raise typer.Exit(code=1)
        
        print(f"[green]✅ Description updated for {result['snapshot_id']}[/green]")
        return
    
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
    
    # ========================================================================
    # SHOW SPECIFIC SNAPSHOT
    # ========================================================================
    if version:
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
        return
    
    # ========================================================================
    # LIST SNAPSHOTS (default action)
    # ========================================================================
    result = snapshot_service.list_snapshots(limit=limit)
    
    if not result["success"]:
        print(f"[red]❌ Failed to list snapshots: {result['error']}[/red]")
        raise typer.Exit(code=1)
    
    if result["count"] == 0:
        print("[yellow]No snapshots found. Create one with 'ddoc snapshot -m \"message\"'[/yellow]")
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


# DEPRECATED: Legacy commands (kept for backwards compatibility, will be removed in v2.1)
def commit(
    message: str = typer.Option(..., "--message", "-m", help="Snapshot description message"),
    alias: Optional[str] = typer.Option(None, "--alias", "-a", help="Alias for this snapshot"),
):
    """[DEPRECATED] Use 'ddoc snapshot -m' instead."""
    print("[yellow]⚠️  'ddoc commit' is deprecated. Use 'ddoc snapshot -m' instead.[/yellow]\n")
    snapshot(message=message, alias=alias)


def checkout(
    version_or_alias: str = typer.Argument(..., help="Snapshot ID (v01) or alias (baseline)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force checkout"),
):
    """[DEPRECATED] Use 'ddoc snapshot --restore' instead."""
    print("[yellow]⚠️  'ddoc checkout' is deprecated. Use 'ddoc snapshot --restore' instead.[/yellow]\n")
    snapshot(restore=version_or_alias, force=force)


def log(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Maximum number of snapshots"),
    oneline: bool = typer.Option(False, "--oneline", help="Compact format"),
):
    """[DEPRECATED] Use 'ddoc snapshot --list' instead."""
    print("[yellow]⚠️  'ddoc log' is deprecated. Use 'ddoc snapshot --list' instead.[/yellow]\n")
    snapshot(list_snapshots=True, limit=limit, oneline=oneline)


def status():
    """[DEPRECATED] Use 'git status' instead."""
    print("[yellow]⚠️  'ddoc status' is deprecated. Use 'git status' directly.[/yellow]\n")


def alias_cmd(
    version: Optional[str] = typer.Argument(None, help="Snapshot version ID"),
    name: Optional[str] = typer.Argument(None, help="Alias name"),
    delete: Optional[str] = typer.Option(None, "--delete", "-d", help="Delete alias"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all aliases"),
):
    """[DEPRECATED] Use 'ddoc snapshot --set-alias' or '--show-aliases' instead."""
    print("[yellow]⚠️  'ddoc alias' is deprecated. Use 'ddoc snapshot --set-alias/--show-aliases' instead.[/yellow]\n")
    if list_all:
        snapshot(show_aliases=True)
    elif delete:
        snapshot(unalias=delete)
    elif version and name:
        snapshot(set_alias=[version, name])


def diff(
    version1: str = typer.Argument(..., help="First snapshot ID or alias"),
    version2: str = typer.Argument(..., help="Second snapshot ID or alias"),
):
    """[DEPRECATED] Use 'ddoc snapshot --diff' instead."""
    print("[yellow]⚠️  'ddoc diff' is deprecated. Use 'ddoc snapshot --diff' instead.[/yellow]\n")
    snapshot(diff=[version1, version2])


# ============================================================================
# OLD Init command (for reference, will be deprecated)
# ============================================================================

def init_old(
    setup_prompt: bool = typer.Option(True, "--setup-prompt/--no-setup-prompt", help="Setup shell prompt integration"),
):
    """
    [DEPRECATED] Old init command. Use 'ddoc init <path>' instead.
    
    Initializes DVC, creates .dvcignore, and optionally sets up shell prompt integration.
    
    Examples:
        ddoc init  # Initialize DVC, .dvcignore, and shell prompt
        ddoc init --no-setup-prompt  # Initialize without prompt setup
    """
    print(f"[bold cyan]🚀 Initializing ddoc project...[/bold cyan]")
    
    # Check if DVC is initialized
    project_root = Path(".")
    dvc_dir = project_root / ".dvc"
    
    if not dvc_dir.exists():
        print("   Initializing DVC...")
        try:
            core_ops = get_core_ops()
            result = core_ops._run_dvc_command(["init"], "DVC initialization")
            if result.get("success"):
                print("   ✅ DVC initialized")
            else:
                print(f"   ⚠️ DVC initialization may have failed")
        except Exception as e:
            print(f"   ⚠️ DVC initialization error: {e}")
    else:
        print("   ✅ DVC already initialized")
    
    # Check/create .dvcignore
    dvcignore_path = project_root / ".dvcignore"
    if not dvcignore_path.exists():
        try:
            from ddoc.core.dataset_service import get_dataset_service
            service = get_dataset_service(".")
            service._create_dvcignore_file(project_root)
            print("   ✅ Created .dvcignore")
        except Exception:
            pass
    else:
        print("   ✅ .dvcignore already exists")
    
    # Setup shell prompt integration
    if setup_prompt:
        print("\n[bold cyan]📝 Setting up shell prompt integration...[/bold cyan]")
        
        # Detect shell
        shell_env = os.environ.get('SHELL', '').lower()
        if 'zsh' in shell_env:
            shell = 'zsh'
            config_file = Path.home() / ".zshrc"
        elif 'bash' in shell_env:
            shell = 'bash'
            config_file = Path.home() / ".bashrc"
        else:
            shell = 'zsh'
            config_file = Path.home() / ".zshrc"
        
        print(f"   Detected shell: {shell}")
        print(f"   Config file: {config_file}")
        
        # Check if already configured
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '_ddoc_chpwd' in content or '_ddoc_update_env' in content:
                    print(f"   ⚠️ Shell prompt already configured in {config_file}")
                    print(f"   [yellow]💡 To update, manually remove old configuration and run 'ddoc init' again[/yellow]")
                    print(f"\n[green]✅ Project initialization complete![/green]")
                    return
        
        # Generate shell script
        shell_script = []
        if shell == "zsh":
            shell_script = [
                "",
                "# ddoc shell prompt integration (auto-detected .ddoc_current file)",
                "# Auto-detect ddoc dataset from .ddoc_current file (chpwd hook)",
                "_ddoc_chpwd() {",
                '  local dir="$(pwd)"',
                '  local ddoc_file=""',
                '  # Search for .ddoc_current file from current directory up to home',
                '  while [ "$dir" != "$HOME" ] && [ "$dir" != "/" ]; do',
                '    if [ -f "$dir/.ddoc_current" ]; then',
                '      ddoc_file="$dir/.ddoc_current"',
                '      break',
                '    fi',
                '    dir="$(dirname "$dir")"',
                '  done',
                '  if [ -n "$ddoc_file" ] && [ -f "$ddoc_file" ]; then',
                '    export DDOC_DATASET=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1])).get(\\"dataset\\", \\"\\"))" "$ddoc_file" 2>/dev/null)',
                '    export DDOC_VERSION=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1])).get(\\"version\\", \\"\\"))" "$ddoc_file" 2>/dev/null)',
                '  else',
                '    unset DDOC_DATASET',
                '    unset DDOC_VERSION',
                '  fi',
                '}',
                "",
                "# Hook chpwd to auto-detect ddoc dataset",
                "autoload -Uz add-zsh-hook",
                "add-zsh-hook chpwd _ddoc_chpwd",
                "",
                "# Also run on shell start",
                "_ddoc_chpwd",
                "",
                "# Update prompt function - also reload file on each prompt",
                "# This function runs after other precmd hooks to preserve venv/conda prompts",
                "_ddoc_precmd() {",
                '  # Reload .ddoc_current file on each prompt to catch updates',
                '  _ddoc_chpwd',
                '  ',
                '  # Get current PROMPT (may already include venv/conda from p10k, oh-my-zsh, etc.)',
                '  local current_prompt="$PROMPT"',
                '  ',
                '  # Remove existing ddoc prefix if present to avoid duplication',
                '  # Use sed to remove [ddoc:...@...] pattern from the beginning',
                '  current_prompt=$(echo "$current_prompt" | sed -E "s/^\\[ddoc:[^]]*\\] //")',
                '  ',
                '  # Add ddoc prefix if dataset and version are set',
                '  if [ -n "$DDOC_DATASET" ] && [ -n "$DDOC_VERSION" ]; then',
                '    PROMPT="[ddoc:$DDOC_DATASET@$DDOC_VERSION] $current_prompt"',
                '  else',
                '    PROMPT="$current_prompt"',
                '  fi',
                '}',
                "",
                "# Hook precmd to update prompt (runs after other hooks to preserve venv/conda)",
                "# This hook runs after p10k and other prompt generators to preserve their output",
                "add-zsh-hook precmd _ddoc_precmd",
            ]
        elif shell == "bash":
            shell_script = [
                "",
                "# ddoc shell prompt integration (auto-detected .ddoc_current file)",
                "# Auto-detect ddoc dataset from .ddoc_current file",
                "_ddoc_update_env() {",
                '  local dir="$(pwd)"',
                '  local ddoc_file=""',
                '  # Search for .ddoc_current file from current directory up to home',
                '  while [ "$dir" != "$HOME" ] && [ "$dir" != "/" ]; do',
                '    if [ -f "$dir/.ddoc_current" ]; then',
                '      ddoc_file="$dir/.ddoc_current"',
                '      break',
                '    fi',
                '    dir="$(dirname "$dir")"',
                '  done',
                '  if [ -n "$ddoc_file" ] && [ -f "$ddoc_file" ]; then',
                '    export DDOC_DATASET=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1])).get(\\"dataset\\", \\"\\"))" "$ddoc_file" 2>/dev/null)',
                '    export DDOC_VERSION=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1])).get(\\"version\\", \\"\\"))" "$ddoc_file" 2>/dev/null)',
                '  else',
                '    unset DDOC_DATASET',
                '    unset DDOC_VERSION',
                '  fi',
                '}',
                "",
                "# Save original PS1",
                'if [ -z "$DDOC_PS1_BASE" ]; then',
                '  export DDOC_PS1_BASE="$PS1"',
                'fi',
                "",
                "# Update prompt function to include ddoc info",
                "_ddoc_update_prompt() {",
                '  if [ -n "$DDOC_DATASET" ] && [ -n "$DDOC_VERSION" ]; then',
                '    PS1="[ddoc:$DDOC_DATASET@$DDOC_VERSION] $DDOC_PS1_BASE"',
                '  else',
                '    PS1="$DDOC_PS1_BASE"',
                '  fi',
                '}',
                "",
                "# Hook PROMPT_COMMAND to auto-detect and update prompt",
                'if [ -z "$PROMPT_COMMAND" ]; then',
                '  PROMPT_COMMAND="_ddoc_update_env; _ddoc_update_prompt"',
                'else',
                '  PROMPT_COMMAND="_ddoc_update_env; _ddoc_update_prompt; $PROMPT_COMMAND"',
                'fi',
                "",
                "# Run once on shell start",
                "_ddoc_update_env",
                "_ddoc_update_prompt",
            ]
        
        # Append to config file
        try:
            with open(config_file, 'a', encoding='utf-8') as f:
                f.write('\n'.join(shell_script) + '\n')
            print(f"   ✅ Added shell prompt integration to {config_file}")
            print(f"   [yellow]💡 Restart your shell or run: source {config_file}[/yellow]")
        except Exception as e:
            print(f"   ⚠️ Failed to write to {config_file}: {e}")
            print(f"   [yellow]💡 Please manually add the following to {config_file}:[/yellow]")
            print("")
            for line in shell_script:
                print(f"   {line}")
    
    print(f"\n[green]✅ Project initialization complete![/green]")


def register(app: typer.Typer) -> None:
    """Attach all commands to the given Typer app."""
    
    # ============================================================================
    # NEW v2.0 Commands (git-like workflow)
    # ============================================================================
    # ========================================================================
    # CORE v2.0 Commands
    # ========================================================================
    # 0. Init command (scaffolding)
    app.command(name="init")(init)
    
    # 1. Add command (data/code/notebook)
    app.command(name="add")(add)
    
    # 2. UNIFIED Snapshot management (replaces commit/checkout/log/status/alias/diff/lineage)
    app.command(name="snapshot")(snapshot)
    
    # ========================================================================
    # DEPRECATED v1.x Commands (backwards compatibility, will be removed in v2.1)
    # ========================================================================
    app.command(name="commit", hidden=True)(commit)
    app.command(name="checkout", hidden=True)(checkout)
    app.command(name="log", hidden=True)(log)
    app.command(name="status", hidden=True)(status)
    app.command(name="alias", hidden=True)(alias_cmd)
    app.command(name="diff", hidden=True)(diff)
    
    # ========================================================================
    # Active v2.0 Subcommands (analysis, experiments, plugins)
    # ========================================================================
    app.add_typer(analyze_app, name="analyze")
    app.add_typer(exp_app, name="exp")
    app.add_typer(plugin_app, name="plugin")
    
    # ========================================================================
    # Visualization
    # ========================================================================
    app.command()(vis)
    
    # ========================================================================
    # REMOVED: dataset & lineage subcommands (functionality moved to 'snapshot')
    # ========================================================================
    # app.add_typer(dataset_app, name="dataset")  # REMOVED in v2.0
    # app.add_typer(lineage_app, name="lineage")  # REMOVED in v2.0 (use 'snapshot --graph')