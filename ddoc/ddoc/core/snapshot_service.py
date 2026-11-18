"""
Snapshot management service for ddoc
"""
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import subprocess

from .schemas import Snapshot, DataSnapshot, CodeSnapshot, ExperimentSnapshot, LineageSnapshot, AliasMapping
from .git_service import get_git_service
from rich import print


class SnapshotService:
    """Service for managing snapshots (commit/checkout)"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.ddoc_dir = self.project_root / ".ddoc"
        self.snapshots_dir = self.ddoc_dir / "snapshots"
        self.aliases_file = self.snapshots_dir / "aliases.json"
        self.git_service = get_git_service(str(self.project_root))
        
        # Ensure directories exist
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    def create_snapshot(
        self,
        message: str,
        alias: Optional[str] = None,
        include_experiment: bool = True,
        auto_commit: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new snapshot with automatic git/dvc commit
        
        Args:
            message: Snapshot description message
            alias: Optional alias for this snapshot
            include_experiment: Include latest experiment results
            auto_commit: Automatically commit changes (default: True)
            
        Returns:
            Result dictionary with snapshot info
        """
        try:
            # Verify workspace
            if not self._verify_workspace():
                return {
                    "success": False,
                    "error": "Not a valid ddoc workspace. Run 'ddoc init' first."
                }
            
            # Auto-commit workflow
            data_hash_before = None
            data_hash_after = None
            if auto_commit:
                commit_result = self._auto_commit_workflow(message)
                if not commit_result["success"]:
                    return commit_result
                data_hash_before = commit_result.get("data_hash_before")
                data_hash_after = commit_result.get("data_hash_after")
            else:
                # Manual mode: verify clean state
                git_status = self.git_service.get_status()
                if git_status.get("has_uncommitted_changes"):
                    return {
                        "success": False,
                        "error": "Uncommitted changes detected. Commit them first or use auto_commit=True."
                    }
            
            # Generate snapshot ID
            snapshot_id = self._generate_snapshot_id()
            
            # Get current git state
            git_commit = self.git_service.get_current_commit()
            git_branch = self.git_service.get_current_branch()
            
            if not git_commit:
                return {
                    "success": False,
                    "error": "No git commits found. Create at least one git commit first."
                }
            
            # Get DVC data hash (final hash after dvc add)
            data_hash = self._get_dvc_data_hash()
            if not data_hash:
                return {
                    "success": False,
                    "error": "data.dvc not found. Add data first with 'ddoc add --data'"
                }
            
            # If hash changed during auto-commit, copy cache from old hash to new hash
            from .cache_service import get_cache_service
            cache_service = get_cache_service()
            
            if data_hash_before and data_hash_after and data_hash_before != data_hash_after:
                # Check if cache exists for old hash
                old_cache = cache_service.load_analysis_cache(
                    snapshot_id="workspace",
                    data_hash=data_hash_before,
                    cache_type="summary"
                )
                if old_cache:
                    print(f"[cyan]🔄 Copying cache from old hash to new hash...[/cyan]")
                    copy_result = cache_service.copy_cache(data_hash_before, data_hash_after)
                    if copy_result["success"]:
                        print(f"[green]   ✅ Cache copied successfully[/green]")
                        print(f"   📋 Cache types: {', '.join(copy_result.get('cache_types', []))}")
                    else:
                        print(f"[yellow]   ⚠️  Failed to copy cache: {copy_result.get('error')}[/yellow]")
            
            # Get data contents
            data_contents = self._list_data_contents()
            
            # Collect code files
            code_files = self._list_code_files()
            
            # Collect experiment info (optional)
            experiment_info = None
            if include_experiment:
                experiment_info = self._get_latest_experiment()
            
            # Create snapshot object
            snapshot = Snapshot(
                snapshot_id=snapshot_id,
                alias=alias,
                created_at=datetime.now().isoformat(),
                description=message,
                data=DataSnapshot(
                    dvc_hash=data_hash,
                    path="data/",
                    contents=data_contents,
                    stats=self._get_data_stats()
                ),
                code=CodeSnapshot(
                    git_rev=git_commit,
                    branch=git_branch,
                    files=code_files
                ),
                experiment=experiment_info,
                lineage=LineageSnapshot(
                    parent_snapshot=self._get_latest_snapshot_id(),
                    experiments_run=[experiment_info.id] if experiment_info else []
                )
            )
            
            # Save snapshot YAML
            snapshot_file = self.snapshots_dir / f"{snapshot_id}.yaml"
            with open(snapshot_file, 'w') as f:
                yaml.dump(snapshot.model_dump(), f, default_flow_style=False, sort_keys=False)
            
            # Save snapshot to data_hash mapping for cache lookup
            cache_service._save_snapshot_mapping(snapshot_id, data_hash)
            
            print(f"[cyan]🔗 Cache Mapping:[/cyan]")
            print(f"   Snapshot ID: {snapshot_id}")
            print(f"   Data Hash: {data_hash}")
            
            # Check if workspace has analysis cache for this data_hash
            workspace_cache = cache_service.load_analysis_cache(
                snapshot_id="workspace",
                data_hash=data_hash,
                cache_type="summary"
            )
            if workspace_cache:
                print(f"[green]   ✅ Found existing analysis cache (summary)[/green]")
                print(f"   📊 Files analyzed: {workspace_cache.get('num_files', 'N/A')}")
            else:
                print(f"[yellow]   ⚠️  No analysis cache found[/yellow]")
                print(f"   💡 Run 'ddoc analyze eda' to create cache")
            
            # Update alias if provided
            if alias:
                alias_result = self._set_alias(alias, snapshot_id)
                if not alias_result.get("success", True):
                    return {
                        "success": False,
                        "error": alias_result.get("error", "Failed to set alias")
                    }
            
            # Update lineage
            self._update_lineage(snapshot)
            
            # Note: Snapshot metadata (.ddoc/) is NOT committed to Git
            # This ensures snapshot history persists across checkouts
            # Similar to how Git doesn't track .git/ and DVC doesn't track .dvc/
            
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "alias": alias,
                "git_commit": git_commit[:7],
                "data_hash": data_hash[:7],
                "message": message,
                "snapshot_file": str(snapshot_file.relative_to(self.project_root))
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create snapshot: {str(e)}"
            }
    
    def restore_snapshot(
        self,
        version_or_alias: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Restore a snapshot (ddoc checkout)
        
        Args:
            version_or_alias: Snapshot ID or alias
            force: Force checkout even with uncommitted changes
            
        Returns:
            Result dictionary
        """
        try:
            # Resolve alias to version
            snapshot_id = self._resolve_version(version_or_alias)
            if not snapshot_id:
                return {
                    "success": False,
                    "error": f"Snapshot '{version_or_alias}' not found"
                }
            
            # Load snapshot
            snapshot = self._load_snapshot(snapshot_id)
            if not snapshot:
                return {
                    "success": False,
                    "error": f"Failed to load snapshot {snapshot_id}"
                }
            
            # Check for uncommitted changes (excluding .ddoc directory)
            if not force:
                git_status = self.git_service.get_status()
                if git_status.get("has_uncommitted_changes"):
                    # Filter out .ddoc directory changes (snapshot metadata)
                    # git status --porcelain format: "XY path" where X is staged, Y is unstaged
                    changes = git_status.get("changes", [])
                    relevant_changes = []
                    for change in changes:
                        # Extract file path (after status characters and space)
                        # Format: "XY path" or "?? path" for untracked
                        parts = change.strip().split(None, 1)
                        if len(parts) >= 2:
                            file_path = parts[1]
                            # Ignore .ddoc directory changes
                            if not file_path.startswith(".ddoc/"):
                                relevant_changes.append(change)
                        else:
                            # If format is unexpected, include it to be safe
                            relevant_changes.append(change)
                    
                    if relevant_changes:
                        return {
                            "success": False,
                            "error": "You have uncommitted changes. Commit them or use --force to checkout anyway."
                        }
            
            # Checkout git revision
            git_result = self.git_service.checkout(snapshot.code.git_rev, force=force)
            if not git_result["success"]:
                return {
                    "success": False,
                    "error": f"Git checkout failed: {git_result.get('error')}"
                }
            
            # Checkout DVC data
            dvc_result = self._dvc_checkout(force=force)
            if not dvc_result["success"]:
                return {
                    "success": False,
                    "error": f"DVC checkout failed: {dvc_result.get('error')}",
                    "git_restored": True
                }
            
            # Clean up empty directories in data/ after DVC checkout
            # DVC only tracks files, so empty directories remain after checkout
            print("[cyan]🧹 Cleaning up empty directories...[/cyan]")
            data_dir = self.project_root / "data"
            if data_dir.exists():
                # Iterate multiple times to handle nested empty directories
                # After removing child directories, parent may become empty
                total_removed = 0
                max_iterations = 10  # Safety limit
                for iteration in range(max_iterations):
                    removed_count = self._cleanup_empty_directories(data_dir)
                    total_removed += removed_count
                    if removed_count == 0:
                        # No more empty directories found, we're done
                        break
                
                if total_removed > 0:
                    print(f"[green]   ✅ Removed {total_removed} empty director{'y' if total_removed == 1 else 'ies'}[/green]")
            
            # Sync workspace cache with restored snapshot's data hash
            from .cache_service import get_cache_service
            cache_service = get_cache_service(str(self.project_root))
            sync_result = cache_service.sync_workspace_cache(snapshot.data.dvc_hash)
            
            if sync_result.get("synced"):
                print(f"[cyan]🔄 Synced workspace cache to snapshot state[/cyan]")
                print(f"[cyan]   {sync_result['old_hash']} → {sync_result['new_hash']}[/cyan]")
            
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "alias": snapshot.alias,
                "git_commit": snapshot.code.git_rev[:7],
                "data_hash": snapshot.data.dvc_hash[:7],
                "description": snapshot.description,
                "restored_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to restore snapshot: {str(e)}"
            }
    
    def list_snapshots(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        List all snapshots
        
        Args:
            limit: Maximum number of snapshots to return
            
        Returns:
            List of snapshots with metadata
        """
        try:
            snapshots = []
            
            # Get all snapshot files
            snapshot_files = sorted(
                self.snapshots_dir.glob("v*.yaml"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if limit:
                snapshot_files = snapshot_files[:limit]
            
            # Load snapshot metadata
            aliases = self._load_aliases()
            
            for snapshot_file in snapshot_files:
                try:
                    snapshot = self._load_snapshot(snapshot_file.stem)
                    if snapshot:
                        alias = aliases.get_alias(snapshot.snapshot_id)
                        snapshots.append({
                            "snapshot_id": snapshot.snapshot_id,
                            "alias": alias or snapshot.alias,
                            "description": snapshot.description,
                            "created_at": snapshot.created_at,
                            "git_commit": snapshot.code.git_rev[:7],
                            "data_hash": snapshot.data.dvc_hash[:7]
                        })
                except Exception as e:
                    print(f"[yellow]Warning: Failed to load {snapshot_file.name}: {e}[/yellow]")
                    continue
            
            return {
                "success": True,
                "snapshots": snapshots,
                "count": len(snapshots)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list snapshots: {str(e)}"
            }
    
    def get_current_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get current snapshot based on git commit
        
        Returns:
            Current snapshot info or None
        """
        try:
            current_commit = self.git_service.get_current_commit()
            if not current_commit:
                return None
            
            # Find snapshot matching current commit
            for snapshot_file in self.snapshots_dir.glob("v*.yaml"):
                snapshot = self._load_snapshot(snapshot_file.stem)
                if snapshot and snapshot.code.git_rev == current_commit:
                    return {
                        "snapshot_id": snapshot.snapshot_id,
                        "alias": snapshot.alias,
                        "description": snapshot.description,
                        "created_at": snapshot.created_at
                    }
            
            return None
            
        except Exception:
            return None
    
    def get_workspace_state(self) -> Dict[str, Any]:
        """
        Get current workspace state as snapshot-like structure
        
        Returns:
            Dictionary with workspace state information
        """
        try:
            git_commit = self.git_service.get_current_commit() or "uncommitted"
            git_branch = self.git_service.get_current_branch()
            data_hash = self._get_dvc_data_hash() or "unknown"
            data_contents = self._list_data_contents()
            code_files = self._list_code_files()
            
            return {
                "snapshot_id": "workspace",
                "alias": None,
                "is_workspace": True,
                "data": {
                    "path": "data/",
                    "dvc_hash": data_hash,
                    "contents": data_contents,
                    "stats": self._get_data_stats()
                },
                "code": {
                    "git_rev": git_commit,
                    "branch": git_branch,
                    "files": code_files
                }
            }
        except Exception as e:
            return {
                "snapshot_id": "workspace",
                "alias": None,
                "is_workspace": True,
                "error": str(e)
            }
    
    def get_or_create_workspace_snapshot(self) -> Dict[str, Any]:
        """
        Get workspace snapshot info or create temporary snapshot reference
        
        Returns:
            Dictionary with snapshot information (may be workspace state)
        """
        try:
            current_commit = self.git_service.get_current_commit()
            current_data_hash = self._get_dvc_data_hash()
            
            if not current_commit or not current_data_hash:
                # No git/dvc state, return workspace state
                return self.get_workspace_state()
            
            # Try to find matching snapshot
            for snapshot_file in self.snapshots_dir.glob("v*.yaml"):
                snapshot = self._load_snapshot(snapshot_file.stem)
                if snapshot:
                    if (snapshot.code.git_rev == current_commit and 
                        snapshot.data.dvc_hash == current_data_hash):
                        return {
                            "snapshot_id": snapshot.snapshot_id,
                            "alias": snapshot.alias,
                            "is_workspace": False,
                            "snapshot": snapshot
                        }
            
            # No matching snapshot, return workspace state
            return self.get_workspace_state()
            
        except Exception:
            return self.get_workspace_state()
    
    def _verify_workspace(self) -> bool:
        """Verify if current directory is a valid ddoc workspace"""
        required = [self.ddoc_dir, self.project_root / ".git"]
        return all(p.exists() for p in required)
    
    def _generate_snapshot_id(self) -> str:
        """Generate next snapshot ID (v01, v02, ...)"""
        existing = list(self.snapshots_dir.glob("v*.yaml"))
        if not existing:
            return "v01"
        
        # Extract numbers and find max
        numbers = []
        for f in existing:
            try:
                num = int(f.stem[1:])
                numbers.append(num)
            except ValueError:
                continue
        
        next_num = max(numbers) + 1 if numbers else 1
        return f"v{next_num:02d}"
    
    def _get_dvc_data_hash(self) -> Optional[str]:
        """Get DVC hash from data.dvc file"""
        try:
            dvc_file = self.project_root / "data.dvc"
            if not dvc_file.exists():
                return None
            
            with open(dvc_file, 'r') as f:
                dvc_data = yaml.safe_load(f)
            
            if 'outs' in dvc_data and dvc_data['outs']:
                return dvc_data['outs'][0].get('md5')
            
            return None
        except Exception:
            return None
    
    def _list_data_contents(self) -> List[str]:
        """List dataset names in data/ directory"""
        data_dir = self.project_root / "data"
        if not data_dir.exists():
            return []
        
        contents = []
        for item in data_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                contents.append(item.name)
        
        return contents
    
    def _get_data_stats(self) -> Dict[str, Any]:
        """Get statistics about data/ directory"""
        data_dir = self.project_root / "data"
        if not data_dir.exists():
            return {}
        
        total_files = sum(1 for _ in data_dir.rglob('*') if _.is_file())
        total_size = sum(f.stat().st_size for f in data_dir.rglob('*') if f.is_file())
        
        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    def _list_code_files(self) -> List[str]:
        """List code files in code/ directory"""
        code_dir = self.project_root / "code"
        if not code_dir.exists():
            return []
        
        files = []
        for item in code_dir.rglob('*'):
            if item.is_file() and not item.name.startswith('.'):
                files.append(str(item.relative_to(self.project_root)))
        
        return files
    
    def _get_latest_experiment(self) -> Optional[ExperimentSnapshot]:
        """Get latest experiment from experiments/ directory"""
        exp_dir = self.project_root / "experiments"
        if not exp_dir.exists():
            return None
        
        # Find latest experiment directory
        exp_dirs = [d for d in exp_dir.iterdir() if d.is_dir()]
        if not exp_dirs:
            return None
        
        latest_exp = max(exp_dirs, key=lambda x: x.stat().st_mtime)
        
        # Try to load metrics
        metrics_file = latest_exp / "metrics.json"
        metrics = {}
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
            except Exception:
                pass
        
        return ExperimentSnapshot(
            id=latest_exp.name,
            params={},
            metrics=metrics,
            artifacts={}
        )
    
    def _get_latest_snapshot_id(self) -> Optional[str]:
        """Get latest snapshot ID"""
        snapshots = sorted(self.snapshots_dir.glob("v*.yaml"), key=lambda x: x.stat().st_mtime)
        if snapshots:
            return snapshots[-1].stem
        return None
    
    def _load_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Load snapshot from YAML file"""
        try:
            snapshot_file = self.snapshots_dir / f"{snapshot_id}.yaml"
            if not snapshot_file.exists():
                return None
            
            with open(snapshot_file, 'r') as f:
                data = yaml.safe_load(f)
            
            return Snapshot(**data)
        except Exception as e:
            print(f"[yellow]Warning: Failed to load snapshot {snapshot_id}: {e}[/yellow]")
            return None
    
    def _load_aliases(self) -> AliasMapping:
        """Load alias mappings"""
        try:
            if self.aliases_file.exists():
                with open(self.aliases_file, 'r') as f:
                    data = json.load(f)
                return AliasMapping(**data)
            return AliasMapping()
        except Exception:
            return AliasMapping()
    
    def _save_aliases(self, aliases: AliasMapping) -> None:
        """Save alias mappings"""
        with open(self.aliases_file, 'w') as f:
            json.dump(aliases.model_dump(), f, indent=2)
    
    def _set_alias(self, alias: str, version: str) -> Dict[str, Any]:
        """Set an alias for a version"""
        try:
            aliases = self._load_aliases()
            
            # Check if alias already exists and points to different version
            existing_version = aliases.get_version(alias)
            if existing_version and existing_version != version:
                return {
                    "success": False,
                    "error": f"Alias '{alias}' already exists and points to {existing_version}. Use a different alias or update the existing one explicitly."
                }
            
            aliases.set_alias(alias, version)
            self._save_aliases(aliases)
            return {"success": True}
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to set alias: {str(e)}"
            }
    
    def _resolve_version(self, version_or_alias: str) -> Optional[str]:
        """Resolve alias to version ID"""
        # First check if it's a direct version
        snapshot_file = self.snapshots_dir / f"{version_or_alias}.yaml"
        if snapshot_file.exists():
            return version_or_alias
        
        # Check aliases
        aliases = self._load_aliases()
        return aliases.get_version(version_or_alias)
    
    def _dvc_checkout(self, force: bool = False) -> Dict[str, Any]:
        """Run dvc checkout"""
        try:
            cmd = ["dvc", "checkout"]
            if force:
                cmd.append("--force")
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "success": True,
                "message": "DVC data restored"
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"DVC checkout failed: {e.stderr}"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "DVC not found"
            }
    
    def _cleanup_empty_directories(self, path: Path) -> int:
        """
        Recursively remove empty directories in data/ directory.
        
        DVC only tracks files, so when files are removed during checkout,
        empty directories remain. This method cleans them up.
        
        Args:
            path: Path to directory to clean (typically data/)
            
        Returns:
            Number of directories removed
        """
        if not path.exists() or not path.is_dir():
            return 0
        
        removed_count = 0
        # Files that commonly prevent "empty" dirs from being removed after checkout on macOS/Windows.
        junk_names = {".DS_Store", "Thumbs.db", "desktop.ini"}
        
        try:
            # Remove junk files in the current directory first (best-effort).
            for child in list(path.iterdir()):
                try:
                    if child.is_file():
                        if child.name in junk_names or child.name.startswith("._"):
                            child.unlink(missing_ok=True)
                except Exception:
                    pass

            # Get all directory items (excluding files, we only care about dirs)
            # Also exclude .dvc directories (DVC metadata)
            items = [
                item for item in path.iterdir() 
                if item.is_dir() and not item.name.startswith('.') and item.name != '.dvc'
            ]
            
            # Process children first (bottom-up approach)
            for item in items:
                # Recursively clean subdirectories
                removed_count += self._cleanup_empty_directories(item)
            
            # Remove junk files again (children cleanup may have left empty dirs with only junk).
            for child in list(path.iterdir()):
                try:
                    if child.is_file():
                        if child.name in junk_names or child.name.startswith("._"):
                            child.unlink(missing_ok=True)
                except Exception:
                    pass

            # After processing all children, try to remove empty directories at current level
            # Re-check current level after recursive cleanup (children may have been removed)
            # We need to re-iterate because the directory structure may have changed
            remaining_items = [
                item for item in path.iterdir() 
                if item.is_dir() and not item.name.startswith('.') and item.name != '.dvc'
            ]
            
            for item in remaining_items:
                try:
                    # Directly try to remove - rmdir() will fail if directory is not empty
                    # This is more reliable than checking iterdir() first
                    # rmdir() only succeeds if directory is completely empty
                    item.rmdir()
                    removed_count += 1
                except OSError:
                    # Directory not empty (ENOTEMPTY) or permission error - skip
                    # This is expected for non-empty directories
                    # errno.ENOTEMPTY = 39 on Unix, 145 on Windows
                    pass
        except Exception as e:
            # Silently ignore errors during cleanup
            # This is a best-effort operation
            pass
        
        return removed_count
    
    def _update_lineage(self, snapshot: Snapshot) -> None:
        """Update lineage graph with new snapshot"""
        lineage_file = self.ddoc_dir / "lineage" / "lineage.json"
        lineage_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if lineage_file.exists():
                with open(lineage_file, 'r') as f:
                    lineage = json.load(f)
            else:
                lineage = {"snapshots": [], "relationships": []}
            
            # Add snapshot node
            lineage["snapshots"].append({
                "snapshot_id": snapshot.snapshot_id,
                "created_at": snapshot.created_at,
                "description": snapshot.description
            })
            
            # Add relationship to parent if exists
            if snapshot.lineage and snapshot.lineage.parent_snapshot:
                lineage["relationships"].append({
                    "from": snapshot.lineage.parent_snapshot,
                    "to": snapshot.snapshot_id,
                    "type": "parent"
                })
            
            with open(lineage_file, 'w') as f:
                json.dump(lineage, f, indent=2)
                
        except Exception as e:
            print(f"[yellow]Warning: Failed to update lineage: {e}[/yellow]")
    
    def _auto_commit_workflow(self, message: str) -> Dict[str, Any]:
        """
        Automatic git/dvc commit workflow
        
        1. Check if data/ changed → dvc add data/
        2. git add -A
        3. git commit with message
        
        Returns:
            Result dictionary with data_hash_before and data_hash_after
        """
        try:
            # Get current data hash before checking changes
            data_hash_before = self._get_dvc_data_hash() or "unknown"
            print(f"[cyan]📊 Current data_hash: {data_hash_before}[/cyan]")
            
            # Check if data.dvc exists
            data_dvc_file = self.project_root / "data.dvc"
            data_dir = self.project_root / "data"
            
            # If data.dvc doesn't exist, we need to create it (even if data/ is empty)
            if not data_dvc_file.exists():
                if data_dir.exists():
                    print("[cyan]📦 data.dvc not found. Creating initial data.dvc...[/cyan]")
                    result = subprocess.run(
                        ["dvc", "add", "data/"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        return {
                            "success": False,
                            "error": f"DVC add failed: {result.stderr}",
                            "data_hash_before": data_hash_before,
                            "data_hash_after": data_hash_before
                        }
                    
                    # Get new data hash after dvc add
                    data_hash_after = self._get_dvc_data_hash() or "unknown"
                    if data_hash_after != data_hash_before:
                        print(f"[yellow]⚠️  Data hash changed:[/yellow]")
                        print(f"   Before: {data_hash_before}")
                        print(f"   After:  {data_hash_after}")
                    else:
                        print(f"[green]✅ Data hash unchanged: {data_hash_after}[/green]")
                else:
                    # data/ directory doesn't exist, create empty one and track it
                    print("[cyan]📦 data/ directory not found. Creating empty data/ directory...[/cyan]")
                    data_dir.mkdir(parents=True, exist_ok=True)
                    result = subprocess.run(
                        ["dvc", "add", "data/"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        return {
                            "success": False,
                            "error": f"DVC add failed: {result.stderr}",
                            "data_hash_before": data_hash_before,
                            "data_hash_after": data_hash_before
                        }
                    
                    data_hash_after = self._get_dvc_data_hash() or "unknown"
                    print(f"[green]✅ Created empty data/ directory and tracked with DVC[/green]")
            else:
                # data.dvc exists, check if data/ directory has changes
                data_changed = self._has_data_changes()
                print(f"[cyan]🔍 Data changes detected: {data_changed}[/cyan]")
                
                data_hash_after = data_hash_before
                
                if data_changed:
                    print("[cyan]📦 Tracking data changes with DVC...[/cyan]")
                    result = subprocess.run(
                        ["dvc", "add", "data/"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        return {
                            "success": False,
                            "error": f"DVC add failed: {result.stderr}",
                            "data_hash_before": data_hash_before,
                            "data_hash_after": data_hash_before
                        }
                    
                    # Get new data hash after dvc add
                    data_hash_after = self._get_dvc_data_hash() or "unknown"
                    if data_hash_after != data_hash_before:
                        print(f"[yellow]⚠️  Data hash changed:[/yellow]")
                        print(f"   Before: {data_hash_before}")
                        print(f"   After:  {data_hash_after}")
                    else:
                        print(f"[green]✅ Data hash unchanged: {data_hash_after}[/green]")
            
            # Stage all changes
            print("[cyan]📝 Staging changes...[/cyan]")
            git_result = self.git_service.add_all()
            if not git_result.get("success", True):
                return {
                    "success": False,
                    "error": f"Git add failed: {git_result.get('error')}"
                }
            
            # Commit
            print("[cyan]💾 Committing changes...[/cyan]")
            commit_message = f"[ddoc] {message}"
            git_result = self.git_service.commit(commit_message)
            if not git_result["success"]:
                # Check if it's "nothing to commit" - that's OK
                if "nothing to commit" in git_result.get("error", "").lower():
                    return {"success": True, "message": "No changes to commit"}
                return {
                    "success": False,
                    "error": f"Git commit failed: {git_result.get('error')}"
                }
            
            return {
                "success": True,
                "message": "Changes committed successfully",
                "data_hash_before": data_hash_before,
                "data_hash_after": data_hash_after
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Auto-commit workflow failed: {str(e)}",
                "data_hash_before": data_hash_before if 'data_hash_before' in locals() else "unknown",
                "data_hash_after": data_hash_after if 'data_hash_after' in locals() else "unknown"
            }
    
    def _ensure_data_tracked(self) -> Dict[str, Any]:
        """Ensure data is tracked with DVC (idempotent)"""
        try:
            data_dvc = self.project_root / "data.dvc"
            if not data_dvc.exists():
                # No data.dvc, need to track
                result = subprocess.run(
                    ["dvc", "add", "data/"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    return {
                        "success": False,
                        "warning": f"DVC add failed: {result.stderr}"
                    }
                return {"success": True, "action": "tracked"}
            else:
                # data.dvc exists, check if it's up to date
                result = subprocess.run(
                    ["dvc", "status", "data.dvc"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    # Changes detected, re-track
                    result = subprocess.run(
                        ["dvc", "add", "data/"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        return {
                            "success": False,
                            "warning": f"DVC add failed: {result.stderr}"
                        }
                    return {"success": True, "action": "updated"}
                else:
                    # No changes, already tracked
                    return {"success": True, "action": "already_tracked"}
        except Exception as e:
            return {"success": False, "warning": str(e)}
    
    def _has_data_changes(self) -> bool:
        """Check if data/ directory has uncommitted changes"""
        try:
            # Check DVC status for data.dvc
            result = subprocess.run(
                ["dvc", "status", "data.dvc"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            # DVC status returns empty output if no changes
            # If output contains "Pipeline is up to date" or is empty, no changes
            output = result.stdout.strip()
            if not output:
                return False
            
            # Check for actual change indicators (not just status messages)
            # DVC status shows changes with lines like "data.dvc:" or file paths
            # If it's just "Pipeline is up to date", there are no changes
            if "Pipeline is up to date" in output or "Everything is up to date" in output:
                return False
            
            # If output contains data.dvc or file paths, there are changes
            if "data.dvc:" in output or "data/" in output:
                return True
            
            return False
        except Exception:
            # If data.dvc doesn't exist yet, check if data/ has files
            data_dir = self.project_root / "data"
            if data_dir.exists():
                return any(data_dir.iterdir())
            return False
    
    def delete_snapshot(
        self,
        version_or_alias: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a snapshot
        
        Args:
            version_or_alias: Snapshot ID or alias
            force: Skip confirmation
            
        Returns:
            Result dictionary
        """
        try:
            # Resolve version
            snapshot_id = self._resolve_version(version_or_alias)
            if not snapshot_id:
                return {
                    "success": False,
                    "error": f"Snapshot '{version_or_alias}' not found"
                }
            
            # Load snapshot to get details
            snapshot = self._load_snapshot(snapshot_id)
            if not snapshot:
                return {
                    "success": False,
                    "error": f"Failed to load snapshot {snapshot_id}"
                }
            
            # Delete snapshot file
            snapshot_file = self.snapshots_dir / f"{snapshot_id}.yaml"
            snapshot_file.unlink()
            
            # Remove from aliases if present
            aliases = self._load_aliases()
            if snapshot.alias:
                aliases.remove_alias(snapshot.alias)
                self._save_aliases(aliases)
            
            # Remove from lineage
            self._remove_from_lineage(snapshot_id)
            
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "alias": snapshot.alias,
                "message": f"Snapshot {snapshot_id} deleted"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to delete snapshot: {str(e)}"
            }
    
    def verify_snapshot(self, version_or_alias: str) -> Dict[str, Any]:
        """
        Verify snapshot integrity (check if git/dvc references are valid)
        
        Args:
            version_or_alias: Snapshot ID or alias
            
        Returns:
            Result dictionary with verification status
        """
        try:
            # Resolve version
            snapshot_id = self._resolve_version(version_or_alias)
            if not snapshot_id:
                return {
                    "success": False,
                    "error": f"Snapshot '{version_or_alias}' not found"
                }
            
            # Load snapshot
            snapshot = self._load_snapshot(snapshot_id)
            if not snapshot:
                return {
                    "success": False,
                    "error": f"Failed to load snapshot {snapshot_id}"
                }
            
            issues = []
            
            # Verify git commit exists
            result = subprocess.run(
                ["git", "cat-file", "-t", snapshot.code.git_rev],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                issues.append(f"Git commit {snapshot.code.git_rev} not found")
            
            # Verify DVC hash exists (check in cache or remote)
            dvc_file = self.project_root / "data.dvc"
            if dvc_file.exists():
                # Just verify the file exists, actual data verification is complex
                pass
            else:
                issues.append("data.dvc file not found")
            
            return {
                "success": len(issues) == 0,
                "snapshot_id": snapshot_id,
                "issues": issues,
                "message": "Snapshot is valid" if not issues else "Snapshot has issues"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Verification failed: {str(e)}"
            }
    
    def verify_all_snapshots(self) -> Dict[str, Any]:
        """Verify all snapshots"""
        try:
            results = []
            snapshot_files = list(self.snapshots_dir.glob("v*.yaml"))
            
            for snapshot_file in snapshot_files:
                snapshot_id = snapshot_file.stem
                result = self.verify_snapshot(snapshot_id)
                results.append({
                    "snapshot_id": snapshot_id,
                    "valid": result["success"],
                    "issues": result.get("issues", [])
                })
            
            total = len(results)
            valid = sum(1 for r in results if r["valid"])
            
            return {
                "success": True,
                "total": total,
                "valid": valid,
                "invalid": total - valid,
                "results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Verification failed: {str(e)}"
            }
    
    def prune_snapshots(self) -> Dict[str, Any]:
        """
        Remove orphaned/unreferenced snapshots
        Currently just identifies them (safe operation)
        """
        try:
            # Get all snapshots
            all_snapshots = list(self.snapshots_dir.glob("v*.yaml"))
            
            # Load lineage
            lineage_file = self.ddoc_dir / "lineage" / "lineage.json"
            if lineage_file.exists():
                with open(lineage_file, 'r') as f:
                    lineage = json.load(f)
            else:
                lineage = {"snapshots": [], "relationships": []}
            
            # Find orphaned snapshots (no incoming or outgoing relationships)
            referenced = set()
            for rel in lineage.get("relationships", []):
                referenced.add(rel["from"])
                referenced.add(rel["to"])
            
            # Latest snapshot is always referenced
            if all_snapshots:
                latest = max(all_snapshots, key=lambda x: x.stat().st_mtime)
                referenced.add(latest.stem)
            
            orphaned = []
            for snapshot_file in all_snapshots:
                snapshot_id = snapshot_file.stem
                snapshot = self._load_snapshot(snapshot_id)
                if snapshot and snapshot.alias:
                    # Aliased snapshots are always kept
                    referenced.add(snapshot_id)
                elif snapshot_id not in referenced:
                    orphaned.append(snapshot_id)
            
            return {
                "success": True,
                "total_snapshots": len(all_snapshots),
                "referenced": len(referenced),
                "orphaned": len(orphaned),
                "orphaned_list": orphaned,
                "message": f"Found {len(orphaned)} orphaned snapshot(s)"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Prune failed: {str(e)}"
            }
    
    def edit_description(
        self,
        version_or_alias: str,
        new_description: str
    ) -> Dict[str, Any]:
        """
        Edit snapshot description
        
        Args:
            version_or_alias: Snapshot ID or alias
            new_description: New description text
            
        Returns:
            Result dictionary
        """
        try:
            # Resolve version
            snapshot_id = self._resolve_version(version_or_alias)
            if not snapshot_id:
                return {
                    "success": False,
                    "error": f"Snapshot '{version_or_alias}' not found"
                }
            
            # Load snapshot
            snapshot = self._load_snapshot(snapshot_id)
            if not snapshot:
                return {
                    "success": False,
                    "error": f"Failed to load snapshot {snapshot_id}"
                }
            
            # Update description
            snapshot.description = new_description
            
            # Save back to file
            snapshot_file = self.snapshots_dir / f"{snapshot_id}.yaml"
            with open(snapshot_file, 'w') as f:
                yaml.dump(snapshot.model_dump(), f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "new_description": new_description,
                "message": f"Description updated for {snapshot_id}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to edit description: {str(e)}"
            }
    
    def get_lineage_graph(self) -> Dict[str, Any]:
        """
        Get snapshot lineage as a graph structure
        
        Returns:
            Dictionary with nodes and edges for graph visualization
        """
        try:
            # Load lineage
            lineage_file = self.ddoc_dir / "lineage" / "lineage.json"
            if not lineage_file.exists():
                return {
                    "success": True,
                    "nodes": [],
                    "edges": [],
                    "message": "No lineage data found"
                }
            
            with open(lineage_file, 'r') as f:
                lineage = json.load(f)
            
            # Enrich with snapshot details
            nodes = []
            for snap in lineage.get("snapshots", []):
                snapshot = self._load_snapshot(snap["snapshot_id"])
                if snapshot:
                    nodes.append({
                        "id": snapshot.snapshot_id,
                        "alias": snapshot.alias,
                        "description": snapshot.description,
                        "created_at": snapshot.created_at,
                        "git_commit": snapshot.code.git_rev[:7],
                        "data_hash": snapshot.data.dvc_hash[:7]
                    })
            
            edges = lineage.get("relationships", [])
            
            return {
                "success": True,
                "nodes": nodes,
                "edges": edges,
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get lineage graph: {str(e)}"
            }
    
    def _remove_from_lineage(self, snapshot_id: str) -> None:
        """Remove snapshot from lineage graph"""
        try:
            lineage_file = self.ddoc_dir / "lineage" / "lineage.json"
            if not lineage_file.exists():
                return
            
            with open(lineage_file, 'r') as f:
                lineage = json.load(f)
            
            # Remove snapshot node
            lineage["snapshots"] = [
                s for s in lineage["snapshots"]
                if s["snapshot_id"] != snapshot_id
            ]
            
            # Remove related relationships
            lineage["relationships"] = [
                r for r in lineage["relationships"]
                if r["from"] != snapshot_id and r["to"] != snapshot_id
            ]
            
            with open(lineage_file, 'w') as f:
                json.dump(lineage, f, indent=2)
                
        except Exception as e:
            print(f"[yellow]Warning: Failed to update lineage: {e}[/yellow]")


def get_snapshot_service(project_root: Optional[str] = None) -> SnapshotService:
    """Factory function to get snapshot service instance"""
    return SnapshotService(project_root)

