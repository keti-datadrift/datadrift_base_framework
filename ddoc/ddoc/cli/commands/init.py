"""Project initialization command"""
import typer
from rich import print


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
    print(f"  4. ddoc snapshot -m \"Initial baseline\" -a baseline")
    print()

