"""
Workspace management for ddoc projects
"""
from pathlib import Path
from typing import Dict, Any, Optional
import os
import subprocess
import shutil
from rich import print


class WorkspaceService:
    """Service for managing ddoc workspace structure"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
    
    def init_workspace(self, project_path: str, force: bool = False) -> Dict[str, Any]:
        """
        Initialize a new ddoc workspace with scaffolding
        
        Args:
            project_path: Path to create the project (can be relative or absolute)
            force: If True, initialize even if directory exists
            
        Returns:
            Result dictionary with success status and created structure info
        """
        try:
            target_path = Path(project_path).resolve()
            
            # Check if directory exists
            if target_path.exists() and not force:
                if any(target_path.iterdir()):
                    return {
                        "success": False,
                        "error": f"Directory {target_path} already exists and is not empty. Use --force to initialize anyway."
                    }
            
            # Create main directory
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Create workspace structure
            directories = [
                "data",
                "code",
                "code/trainers",  # Trainer code directory
                "models",         # Pretrained models directory
                "notebooks",
                "experiments",
                ".ddoc/snapshots",
                ".ddoc/cache",
                ".ddoc/lineage"
            ]
            
            created_dirs = []
            for dir_name in directories:
                dir_path = target_path / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(dir_path.relative_to(target_path)))
            
            # Create .ddoc/config.yaml
            config_content = self._generate_config_yaml()
            config_path = target_path / ".ddoc" / "config.yaml"
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Create .gitignore
            gitignore_content = self._generate_gitignore()
            gitignore_path = target_path / ".gitignore"
            with open(gitignore_path, 'w') as f:
                f.write(gitignore_content)
            
            # Create .dvcignore
            dvcignore_content = self._generate_dvcignore()
            dvcignore_path = target_path / ".dvcignore"
            with open(dvcignore_path, 'w') as f:
                f.write(dvcignore_content)

            # Create starter README.md (Round-7 — matches the long-
            # standing test expectation and gives the user a foothold).
            readme_path = target_path / "README.md"
            if not readme_path.exists():
                readme_path.write_text(
                    f"# {target_path.name}\n\n"
                    "ddoc workspace.\n\n"
                    "## Layout\n"
                    "- `data/` — datasets (DVC-tracked)\n"
                    "- `code/` — training / analysis scripts\n"
                    "- `notebooks/` — Jupyter notebooks\n"
                    "- `experiments/` — experiment outputs\n"
                    "- `.ddoc/` — workspace metadata (snapshots, cache)\n\n"
                    "## Quick start\n"
                    "```bash\n"
                    "ddoc add --data ./datasets/your_data\n"
                    "git add . && git commit -m \"initial setup\"\n"
                    "ddoc snapshot create -m \"baseline\" -a baseline\n"
                    "ddoc analyze eda\n"
                    "```\n"
                )

            # Initialize git
            git_result = self._init_git(target_path)

            # Initialize dvc
            dvc_result = self._init_dvc(target_path)

            # Round-7 — commit the initial scaffolding so the workspace
            # leaves a clean ``git status``. Previously the .gitignore /
            # .dvcignore / README.md / .dvc/config files sat untracked
            # after init, surfacing as ``has_uncommitted_changes`` for
            # any caller that did a clean ``git status`` immediately
            # afterward (``test_git_operations`` regression).
            if git_result.get("success"):
                self._commit_initial_scaffolding(target_path)

            return {
                "success": True,
                "project_path": str(target_path),
                "created_directories": created_dirs,
                "git_initialized": git_result["success"],
                "dvc_initialized": dvc_result["success"],
                "files_created": [".ddoc/config.yaml", ".gitignore", ".dvcignore", "README.md"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to initialize workspace: {str(e)}"
            }
    
    def _commit_initial_scaffolding(self, project_path: Path) -> None:
        """Stage every file the workspace just generated and create a
        single ``[ddoc] init workspace`` commit. Best-effort — failures
        are swallowed so a partial environment (no git identity, etc.)
        doesn't block ``ddoc init`` itself.
        """
        try:
            r = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_path, capture_output=True, text=True, check=True,
            )
            if not r.stdout.strip():
                return  # nothing to commit
            subprocess.run(
                ["git", "add", "."],
                cwd=project_path, capture_output=True, text=True, check=True,
            )
            env = os.environ.copy()
            env.setdefault("GIT_AUTHOR_NAME", "ddoc")
            env.setdefault("GIT_AUTHOR_EMAIL", "ddoc@local")
            env.setdefault("GIT_COMMITTER_NAME", "ddoc")
            env.setdefault("GIT_COMMITTER_EMAIL", "ddoc@local")
            subprocess.run(
                ["git", "commit", "-m", "[ddoc] init workspace"],
                cwd=project_path, capture_output=True, text=True,
                check=True, env=env,
            )
        except Exception:
            pass

    def _init_git(self, project_path: Path) -> Dict[str, Any]:
        """Initialize git repository"""
        try:
            # Check if git is already initialized
            git_dir = project_path / ".git"
            if git_dir.exists():
                return {"success": True, "message": "Git already initialized"}
            
            # Run git init
            result = subprocess.run(
                ["git", "init"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Configure DVC to use git
            subprocess.run(
                ["git", "config", "core.autoCRLF", "false"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            
            return {"success": True, "message": "Git initialized"}
            
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Git init failed: {e.stderr}"}
        except FileNotFoundError:
            return {"success": False, "error": "Git not found. Please install git first."}
        except Exception as e:
            return {"success": False, "error": f"Git init error: {str(e)}"}
    
    def _init_dvc(self, project_path: Path) -> Dict[str, Any]:
        """Initialize DVC"""
        try:
            # Check if dvc is already initialized
            dvc_dir = project_path / ".dvc"
            if dvc_dir.exists():
                return {"success": True, "message": "DVC already initialized"}
            
            # Run dvc init
            result = subprocess.run(
                ["dvc", "init"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Configure DVC to use git (SCM mode)
            subprocess.run(
                ["dvc", "config", "core.autostage", "true"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            
            return {"success": True, "message": "DVC initialized"}
            
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"DVC init failed: {e.stderr}"}
        except FileNotFoundError:
            return {"success": False, "error": "DVC not found. Please install dvc first: pip install dvc"}
        except Exception as e:
            return {"success": False, "error": f"DVC init error: {str(e)}"}
    
    def _generate_config_yaml(self) -> str:
        """Generate .ddoc/config.yaml content"""
        return """# ddoc project configuration
version: "2.0"
project:
  name: "ddoc_project"
  created_at: ""

snapshot:
  auto_cache: true
  cache_types:
    - summary
    - embedding

tracking:
  mlflow_enabled: true
  lineage_enabled: true
"""
    
    def _generate_gitignore(self) -> str:
        """Generate .gitignore content"""
        return """# ddoc workspace
data/
experiments/
.ddoc/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# Jupyter
.ipynb_checkpoints/
*.ipynb_checkpoints

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
    
    def _generate_dvcignore(self) -> str:
        """Generate .dvcignore content"""
        return """# Add patterns to ignore for DVC

# System files
.DS_Store
._.DS_Store
**/.DS_Store
**/._.DS_Store
Thumbs.db
desktop.ini

# Python cache
*.pyc
*.pyo
__pycache__/
.pytest_cache/

# Git
.git/
.gitignore

# ddoc internal
.ddoc/

# Temporary files
*.tmp
*.temp
.~*
*~
"""
    
    def verify_workspace(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify if the current directory is a valid ddoc workspace
        
        Returns:
            Dictionary with verification results
        """
        path = Path(project_path) if project_path else self.project_root
        
        required_dirs = [".ddoc", ".ddoc/snapshots", ".git"]
        missing_dirs = []
        
        for dir_name in required_dirs:
            if not (path / dir_name).exists():
                missing_dirs.append(dir_name)
        
        is_valid = len(missing_dirs) == 0
        
        return {
            "is_valid": is_valid,
            "missing_directories": missing_dirs,
            "has_git": (path / ".git").exists(),
            "has_dvc": (path / ".dvc").exists(),
            "has_ddoc": (path / ".ddoc").exists()
        }


def get_workspace_service(project_root: Optional[str] = None) -> WorkspaceService:
    """Factory function to get workspace service instance"""
    return WorkspaceService(project_root)

