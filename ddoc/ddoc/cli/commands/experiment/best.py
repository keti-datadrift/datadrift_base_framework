"""
Experiment best command
"""
import typer
from typing import Optional
from rich import print

from ....core.mlflow_experiment_service import get_mlflow_experiment_service
from ..utils import _resolve_dataset_reference


def exp_best_command(
    dataset: str = typer.Argument(..., help="Dataset name or name@version/alias"),
    metric: str = typer.Option("mAP50-95", "--metric", "-m", help="Metric to compare (default: mAP50-95)"),
):
    """
    Find best experiment for a dataset based on a metric.
    
    Only works with MLflow-tracked experiments.
    
    Examples:
        ddoc exp best test_data
        ddoc exp best test_data@v1.0
        ddoc exp best test_data@v1.0 --metric mAP50
        ddoc exp best test_data --metric precision
    """
    try:
        # Parse dataset reference
        dataset_name, version_or_alias = _resolve_dataset_reference(dataset)
        
        # Resolve version if needed
        if version_or_alias:
            try:
                from ....core.version_service import get_version_service
                version_service = get_version_service()
                resolved_version = version_service.get_dataset_version_by_alias(
                    dataset_name, version_or_alias
                )
                if resolved_version:
                    dataset_version = resolved_version
                    print(f"📋 Resolved alias '{version_or_alias}' → {dataset_version}")
                else:
                    dataset_version = version_or_alias
                    print(f"📋 Using version: {dataset_version}")
            except Exception as e:
                print(f"[yellow]⚠️  Version resolution failed: {e}[/yellow]")
                dataset_version = version_or_alias
        else:
            try:
                from ....core.version_service import get_version_service
                version_service = get_version_service()
                status = version_service.get_dataset_status(dataset_name)
                dataset_version = status.get('current_version', 'unknown')
                print(f"📋 Current version: {dataset_version}")
            except Exception as e:
                print(f"[yellow]⚠️  Version check failed: {e}[/yellow]")
                dataset_version = None
        
        print(f"[cyan]🏆 Finding best experiment for {dataset_name}[/cyan]")
        if dataset_version:
            print(f"[cyan]   Version: {dataset_version}[/cyan]")
        print(f"[cyan]   Metric: {metric}[/cyan]\n")
        
        mlflow_service = get_mlflow_experiment_service()
        best = mlflow_service.get_best_experiment_for_dataset(
            dataset_name=dataset_name,
            dataset_version=dataset_version or "unknown",
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
                    value = best.get(col)
                    if value is not None:
                        metric_name = col.replace('metrics.', '')
                        print(f"  {metric_name}: {value}")
            
            # Show tags
            print(f"\n[cyan]Tags:[/cyan]")
            for col in best.keys():
                if col.startswith('tags.'):
                    tag_name = col.replace('tags.', '')
                    tag_value = best.get(col)
                    if tag_value:
                        print(f"  {tag_name}: {tag_value}")
            
            print(f"\n[cyan]💡 View in MLflow UI:[/cyan]")
            print(f"   mlflow ui")
        else:
            print(f"[yellow]⚠️  No experiments found for {dataset_name}[/yellow]")
            if dataset_version:
                print(f"   Version: {dataset_version}")
            print(f"   Metric: {metric}")
            print(f"\n   Try running experiments first:")
            print(f"   ddoc exp train <trainer_name> --dataset {dataset_name}")
    
    except ImportError:
        print(f"[red]❌ MLflow not installed. Install with: pip install mlflow[/red]")
        raise typer.Exit(1)
    except Exception as e:
        print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)

