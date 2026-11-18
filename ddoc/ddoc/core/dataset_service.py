"""
Dataset Service for ddoc
"""
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich import print

from ..ops.core_ops import CoreOpsPlugin
from .version_service import get_version_service
from .metadata_service import get_metadata_service
from .staging_service import get_staging_service


class DatasetService:
    """
    Dataset management service
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.core_ops = CoreOpsPlugin(project_root)
        self.version_service = get_version_service(project_root)
        self.metadata_service = get_metadata_service(project_root)
        self.staging_service = get_staging_service(project_root)
    
    def stage_dataset(
        self, 
        name: str, 
        path: Optional[str] = None,
        formats: List[str] = None,
        config: str = None
    ) -> Dict[str, Any]:
        """
        Stage a dataset for commit (new workflow)
        
        Args:
            name: Dataset name
            path: Dataset path (required for new datasets, optional for modifications)
            formats: File formats to include
            config: Config file name
        
        Returns:
            Result dictionary with success status
        """
        try:
            # Check if dataset already exists (registered)
            mapping = self.metadata_service.get_dataset_mapping(name)
            
            if mapping:
                # Existing dataset - stage modifications
                dataset_path = mapping['dataset_path']
                dvc_file_path = mapping['dvc_file']
                
                # Get previous hash from version history (before updating DVC)
                versions = self.version_service.get_dataset_version_history(name)
                previous_hash = None
                if versions:
                    latest_version = versions[0]
                    previous_hash = latest_version.get('hash')
                
                # Update DVC tracking to detect file changes (additions, deletions, modifications)
                print(f"   Checking for changes in {dataset_path}...")
                try:
                    self.core_ops._run_dvc_command(["add", str(dataset_path)], f"Updating DVC tracking for {name}")
                except Exception as e:
                    print(f"[yellow]Warning: DVC update failed: {e}[/yellow]")
                
                # Get current hash after DVC update
                current_hash = self.version_service.get_dvc_hash(dataset_path)
                if not current_hash:
                    return {"error": f"Could not read DVC hash for dataset {name}"}
                
                # Compare hashes to detect changes
                if previous_hash and current_hash == previous_hash:
                    return {
                        "success": False,
                        "error": f"No changes detected in dataset {name}"
                    }
                
                # Stage the modification
                result = self.staging_service.stage_dataset(
                    name=name,
                    path=dataset_path,
                    operation="modified",
                    formats=formats or [],
                    config=config,
                    current_hash=current_hash
                )
                
                if result.get('success'):
                    print(f"[green]Staged changes: {name}[/green]")
                    print(f"   Hash: {current_hash[:8]}...")
                
                return result
            
            else:
                # New dataset - requires path
                if not path:
                    return {
                        "error": f"Dataset {name} not found. Provide path to register a new dataset."
                    }
                
                dataset_path = Path(path)
                if not dataset_path.exists():
                    return {"error": f"Dataset path {path} does not exist"}
                
                # Verify name matches folder name (consistency check)
                expected_name = dataset_path.name
                if name != expected_name:
                    return {
                        "success": False,
                        "error": (
                            f"Dataset name '{name}' does not match folder name '{expected_name}'.\n"
                            f"  Dataset names must match their folder names for consistency.\n"
                            f"  \n"
                            f"  💡 The dataset will be registered as '{expected_name}'.\n"
                            f"  💡 To add meaningful labels, use version aliases after commit:\n"
                            f"     ddoc dataset commit -m 'message' -a <alias>\n"
                            f"     ddoc dataset tag rename {expected_name} <version> -a <alias>"
                        )
                    }
                
                # Check for duplicates before registering
                try:
                    # Check if name is already used
                    existing_name = self.metadata_service.check_duplicate_name(name)
                    if existing_name:
                        return {
                            "success": False,
                            "error": (
                                f"Dataset name '{name}' is already registered.\n"
                                f"  Existing path: {existing_name['dataset_path']}\n"
                                f"  Registered at: {existing_name.get('registered_at', 'unknown')}\n"
                                f"  \n"
                                f"  💡 To modify this dataset, run: ddoc dataset add {name}\n"
                                f"  💡 To use a different name, run: ddoc dataset add <new_name> {path}"
                            )
                        }
                    
                    # Check if path is already registered
                    existing_path = self.metadata_service.check_duplicate_path(str(dataset_path))
                    if existing_path:
                        return {
                            "success": False,
                            "error": (
                                f"This path is already registered as '{existing_path['name']}'.\n"
                                f"  Path: {existing_path['mapping']['dataset_path']}\n"
                                f"  Registered at: {existing_path['mapping'].get('registered_at', 'unknown')}\n"
                                f"  \n"
                                f"  💡 To use the existing dataset, run: ddoc dataset add {existing_path['name']}\n"
                                f"  💡 To register a different path, specify a different directory"
                            )
                        }
                except ValueError as e:
                    # Duplicate detected by store_dataset_mapping
                    return {
                        "success": False,
                        "error": str(e)
                    }
                
                # Use the original dataset path directly (no copying)
                target_dir = dataset_path
                
                # Initialize DVC if not already initialized
                try:
                    if not (self.project_root / ".dvc").exists():
                        print("   Initializing DVC...")
                        try:
                            self.core_ops._run_dvc_command(["init"], "DVC initialization")
                            print("   ✅ DVC initialized with Git support")
                        except Exception as dvc_init_error:
                            if "not tracked by any supported SCM" in str(dvc_init_error) or "SCM" in str(dvc_init_error):
                                print("   ⚠️ SCM not detected, initializing DVC with --no-scm mode...")
                                self.core_ops._run_dvc_command(["init", "--no-scm"], "DVC initialization (--no-scm)")
                                print("   ✅ DVC initialized in standalone mode (--no-scm)")
                            else:
                                raise dvc_init_error
                except Exception as e:
                    print(f"[yellow]Warning: DVC initialization failed: {e}[/yellow]")
                    print("[yellow]Continuing with dataset registration...[/yellow]")
                
                # Create .dvcignore file
                self._create_dvcignore_file(target_dir)
                
                # Initialize DVC tracking
                self.core_ops._run_dvc_command(["add", str(target_dir)], f"Adding dataset {name} to DVC")
                
                # Get DVC hash
                current_hash = self.version_service.get_dvc_hash(str(target_dir))
                
                # Store dataset name mapping in metadata service
                dvc_file_path = target_dir.with_suffix('.dvc')
                self.metadata_service.store_dataset_mapping(name, str(dvc_file_path), str(target_dir))
                
                # Update params.yaml if config provided
                if config:
                    self._update_params_yaml(name, config)
                
                # Stage the new dataset
                result = self.staging_service.stage_dataset(
                    name=name,
                    path=str(target_dir),
                    operation="new",
                    formats=formats or [],
                    config=config,
                    current_hash=current_hash
                )
                
                if result.get('success'):
                    print(f"[green]Staged new dataset: {name}[/green]")
                    print(f"   Path: {target_dir}")
                    print(f"   Hash: {current_hash[:8] if current_hash else 'N/A'}...")
                
                return result
            
        except Exception as e:
            return {"error": f"Failed to stage dataset: {e}"}
    
    def register_dataset(
        self, 
        name: str, 
        path: str, 
        formats: List[str] = None,
        config: str = None,
        create_branch: bool = True
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Use stage_dataset() instead.
        This method is kept for backward compatibility.
        """
        print("[yellow]⚠️  Warning: register_dataset is deprecated. Use 'ddoc dataset add' followed by 'ddoc dataset commit'[/yellow]")
        
        # Stage the dataset
        stage_result = self.stage_dataset(name, path, formats, config)
        if not stage_result.get('success'):
            return stage_result
        
        # Auto-commit for backward compatibility
        commit_result = self.commit_staged_datasets(
            message=f"Add dataset {name} (legacy)",
            tag=None
        )
        
        return commit_result
    
    def _update_params_yaml(self, name: str, config: str):
        """Update params.yaml with dataset configuration"""
        try:
            params_file = self.project_root / "params.yaml"
            if params_file.exists():
                with open(params_file, 'r') as f:
                    params = yaml.safe_load(f) or {}
            else:
                params = {}
            
            # Add dataset configuration
            if 'datasets' not in params:
                params['datasets'] = {}
            
            params['datasets'][name] = {
                'path': f"data/{name}",
                'config': config,
                'created_at': datetime.now().isoformat()
            }
            
            with open(params_file, 'w') as f:
                yaml.dump(params, f, default_flow_style=False)
            
            # Stage params.yaml
            # Git operations (optional - only if Git repository exists)
            if (self.project_root / ".git").exists():
                try:
                    self.core_ops._run_git_command(["add", "params.yaml"], "Staging params.yaml")
                except Exception:
                    pass  # Git command failed, skip
            
        except Exception as e:
            print(f"Warning: Failed to update params.yaml: {e}")
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all registered datasets using stored mappings"""
        # Auto-migrate existing datasets if needed
        mappings = self.metadata_service.get_all_dataset_mappings()
        if not mappings['datasets']:
            # No mappings exist, try to migrate existing DVC files
            self.migrate_existing_datasets()
            mappings = self.metadata_service.get_all_dataset_mappings()
        
        datasets = []
        
        for dataset_name, mapping_info in mappings['datasets'].items():
            dvc_file_path = Path(mapping_info['dvc_file'])
            dataset_path = Path(mapping_info['dataset_path'])
            
            # Verify that the DVC file and dataset path still exist
            if dvc_file_path.exists() and dataset_path.exists():
                datasets.append({
                    'name': dataset_name,  # User-defined name
                    'path': str(dataset_path),  # Actual dataset path
                    'dvc_file': str(dvc_file_path),  # DVC file path
                    'registered_at': mapping_info.get('registered_at', ''),
                    'formats': self._get_dataset_formats(dataset_path)
                })
        
        # Sort by registration time (newest first)
        datasets.sort(key=lambda x: x.get('registered_at', ''), reverse=True)
        
        return datasets
    
    def migrate_existing_datasets(self):
        """Migrate existing DVC files to the new mapping system"""
        print("[yellow]🔄 Migrating existing datasets to new mapping system...[/yellow]")
        
        # Find all .dvc files that aren't in the mapping system
        existing_mappings = self.metadata_service.get_all_dataset_mappings()
        mapped_dvc_files = {info['dvc_file'] for info in existing_mappings['datasets'].values()}
        
        migrated_count = 0
        for dvc_file in self.project_root.rglob("*.dvc"):
            if dvc_file.is_file() and str(dvc_file) not in mapped_dvc_files:
                try:
                    # Get dataset info from DVC file
                    with open(dvc_file, 'r') as f:
                        import yaml
                        dvc_data = yaml.safe_load(f)
                        if 'outs' in dvc_data and dvc_data['outs']:
                            dataset_path = Path(dvc_data['outs'][0]['path'])
                            if not dataset_path.is_absolute():
                                dataset_path = dvc_file.parent / dataset_path
                            
                            if dataset_path.exists():
                                # Use DVC file name as dataset name for migration
                                dataset_name = dvc_file.stem
                                
                                # Store the mapping
                                self.metadata_service.store_dataset_mapping(
                                    dataset_name, 
                                    str(dvc_file), 
                                    str(dataset_path)
                                )
                                
                                print(f"  ✅ Migrated: {dataset_name} -> {dataset_path}")
                                migrated_count += 1
                except Exception as e:
                    print(f"  ⚠️ Failed to migrate {dvc_file}: {e}")
        
        if migrated_count > 0:
            print(f"[green]✅ Successfully migrated {migrated_count} datasets[/green]")
        else:
            print("[green]✅ No datasets needed migration[/green]")
    
    def _get_dataset_formats(self, dataset_path: Path) -> List[str]:
        """Get file formats in dataset"""
        formats = set()
        for file_path in dataset_path.rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                if suffix:
                    formats.add(suffix)
        return list(formats)
    
    def commit_staged_datasets(
        self,
        message: str,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Commit all staged datasets and create versions
        
        Args:
            message: Commit message
            tag: Optional version tag (if not provided, auto-generated)
        
        Returns:
            Result dictionary with committed datasets
        """
        try:
            # Get staged changes
            staged = self.staging_service.get_staged_changes()
            if not staged.get('success'):
                return staged
            
            if staged.get('total') == 0:
                return {
                    "success": False,
                    "error": "No changes staged for commit"
                }
            
            committed_datasets = []
            errors = []
            
            # Process new datasets
            for dataset_info in staged.get('new', []):
                name = dataset_info['name']
                
                # Create initial version
                version = tag if tag else "v1.0"
                result = self.version_service.create_dataset_version(
                    name=name,
                    version=version,
                    message=message
                )
                
                if result.get("success"):
                    # Add to lineage
                    self.metadata_service.add_dataset(
                        dataset_id=f"{name}@{version}",
                        dataset_name=name,
                        version=version,
                        metadata={
                            "path": dataset_info.get('path'),
                            "formats": dataset_info.get('formats', []),
                            "config": dataset_info.get('config'),
                            "hash": result.get("hash"),
                            "message": message
                        }
                    )
                    
                    # Save current checkout info
                    self._save_current_checkout_file(name, version)
                    
                    committed_datasets.append({
                        "name": name,
                        "version": version,
                        "operation": "new"
                    })
                else:
                    errors.append(f"{name}: {result.get('error')}")
            
            # Process modified datasets
            for dataset_info in staged.get('modified', []):
                name = dataset_info['name']
                
                # Generate next version if tag not provided
                if tag:
                    version = tag
                else:
                    version = self.version_service.generate_next_version(name)
                
                result = self.version_service.create_dataset_version(
                    name=name,
                    version=version,
                    message=message
                )
                
                if result.get("success"):
                    # Add to lineage
                    self.metadata_service.add_dataset(
                        dataset_id=f"{name}@{version}",
                        dataset_name=name,
                        version=version,
                        metadata={
                            "path": dataset_info.get('path'),
                            "formats": dataset_info.get('formats', []),
                            "config": dataset_info.get('config'),
                            "hash": result.get("hash"),
                            "message": message
                        }
                    )
                    
                    # Save current checkout info
                    self._save_current_checkout_file(name, version)
                    
                    committed_datasets.append({
                        "name": name,
                        "version": version,
                        "operation": "modified"
                    })
                else:
                    errors.append(f"{name}: {result.get('error')}")
            
            # Git commit (optional)
            if (self.project_root / ".git").exists():
                try:
                    self.core_ops._run_git_command(["add", "."], "Staging changes")
                    self.core_ops._run_git_command(
                        ["commit", "-m", f"{message}\n\nDatasets: {', '.join([d['name'] for d in committed_datasets])}"],
                        "Committing changes"
                    )
                except Exception as git_error:
                    print(f"[yellow]Warning: Git commit skipped: {git_error}[/yellow]")
            
            # Clear staging area
            self.staging_service.clear_staging()
            
            return {
                "success": True,
                "committed": committed_datasets,
                "errors": errors,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Failed to commit staged datasets: {e}"}
    
    def get_full_status(self) -> Dict[str, Any]:
        """
        Get full status of all datasets (git status style)
        
        Returns:
            Dictionary with staged, unstaged, and untracked datasets
        """
        try:
            # Get staged changes
            staged_result = self.staging_service.get_staged_changes()
            if not staged_result.get('success'):
                return staged_result
            
            staged_new = staged_result.get('new', [])
            staged_modified = staged_result.get('modified', [])
            
            # Get all registered datasets
            all_datasets = self.list_datasets()
            
            # Check for unstaged changes
            unstaged_modified = []
            for dataset in all_datasets:
                name = dataset['name']
                
                # Skip if already staged
                if self.staging_service.is_staged(name):
                    continue
                
                # Check for modifications
                status = self.version_service.get_dataset_status(name)
                if status.get('state') == 'modified':
                    unstaged_modified.append({
                        'name': name,
                        'path': dataset['path'],
                        'old_hash': status.get('latest_hash'),
                        'new_hash': status.get('current_hash')
                    })
            
            # TODO: Detect untracked datasets (DVC files without mapping)
            # This is optional for now
            untracked = []
            
            return {
                'success': True,
                'staged': {
                    'new': staged_new,
                    'modified': staged_modified
                },
                'unstaged': {
                    'modified': unstaged_modified
                },
                'untracked': untracked
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to get status: {e}"
            }
    
    def create_version(self, name: str, tag: str, message: str) -> Dict[str, Any]:
        """
        DEPRECATED: Use commit_staged_datasets() instead.
        Create a version tag for dataset
        """
        print("[yellow]⚠️  Warning: create_version is deprecated. Use 'ddoc dataset commit' instead[/yellow]")
        try:
            # Use VersionService to create version
            result = self.version_service.create_dataset_version(name, tag, message)
            
            if result.get("success"):
                # Add to lineage
                self.metadata_service.add_dataset(
                    dataset_id=f"{name}@{tag}",
                    dataset_name=name,
                    version=tag,
                    metadata={
                        "hash": result.get("hash"),
                        "message": message,
                        "timestamp": result.get("timestamp"),
                        "alias": result.get("alias")
                    }
                )
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to create version: {e}"}
    
    def get_version_history(self, name: str) -> List[Dict[str, Any]]:
        """Get version history for dataset"""
        return self.version_service.get_dataset_version_history(name)

    def list_versions(self, name: str) -> List[Dict[str, Any]]:
        """List dataset versions with alias information"""
        return self.version_service.list_dataset_versions(name)

    def set_version_alias(self, name: str, version: str, alias: Optional[str]) -> Dict[str, Any]:
        """Set or remove alias for dataset version"""
        result = self.version_service.set_dataset_version_alias(name, version, alias)

        if result.get("success"):
            dataset_id = f"{name}@{result.get('version')}"
            self.metadata_service.update_dataset_alias(dataset_id, result.get("alias"))

        return result

    def get_version_by_alias(self, name: str, alias: str) -> Optional[str]:
        """Resolve alias to actual version identifier"""
        return self.version_service.get_dataset_version_by_alias(name, alias)

    def get_dataset_timeline(self, name: str) -> List[Dict[str, Any]]:
        """Return chronological timeline for dataset."""
        return self.metadata_service.get_dataset_timeline(name)
    
    def get_dataset_status(self, name: str) -> Dict[str, Any]:
        """Get dataset version status"""
        return self.version_service.get_dataset_status(name)
    
    def checkout_version(self, name: str, tag: str, pull: bool = True, dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
        """Checkout specific dataset version with automatic strategy selection"""
        try:
            current_status = self.version_service.get_dataset_status(name)
            previous_version = current_status.get("current_version") if current_status else None
            # Get version information
            versions = self.version_service.get_dataset_version_history(name)
            version_data = next((v for v in versions if v["version"] == tag), None)
            
            if not version_data:
                return {"error": f"Version {tag} not found for dataset {name}"}
            
            # Get dataset mapping
            mapping = self.metadata_service.get_dataset_mapping(name)
            if not mapping:
                return {"error": f"Dataset mapping not found for {name}"}
            
            dataset_path = mapping['dataset_path']
            dvc_file_path = mapping['dvc_file']
            
            # Determine restore strategy
            restore_strategy = version_data.get("restore_strategy", "dvc-only")
            
            if dry_run:
                return {
                    "success": True,
                    "dataset": name,
                    "version": tag,
                    "strategy": restore_strategy,
                    "dataset_path": dataset_path,
                    "dvc_file": dvc_file_path,
                    "target_hash": version_data["hash"],
                    "dry_run": True,
                    "message": f"Would restore {name} to {tag} using {restore_strategy} strategy"
                }
            
            # Execute restore based on strategy
            if restore_strategy == "git+dvc":
                result = self._checkout_with_git(name, tag, version_data, dataset_path, dvc_file_path, pull, force)
            else:
                result = self._checkout_without_git(name, tag, version_data, dataset_path, dvc_file_path, pull, force)
            
            # Save current checkout info to file for shell hooks
            if result.get("success"):
                self._save_current_checkout_file(name, tag)
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to checkout version: {e}"}
    
    def _save_current_checkout_file(self, name: str, version: str) -> None:
        """Save current checkout info to .ddoc_current file for shell hooks"""
        try:
            # Save to current working directory so shell hooks can find it
            import os
            current_work_dir = Path(os.getcwd())
            current_file = current_work_dir / ".ddoc_current"
            checkout_info = {
                "dataset": name,
                "version": version,
                "timestamp": datetime.now().isoformat(),
                "project_root": str(current_work_dir.resolve())
            }
            with open(current_file, 'w', encoding='utf-8') as f:
                json.dump(checkout_info, f, indent=2)
            # Force shell hook to reload by triggering chpwd in zsh
            # This is a hint for shell hooks to reload
        except Exception as e:
            # Silently fail - this is just a convenience feature
            # But log in debug mode if needed
            pass
    
    def _has_git_repository(self) -> bool:
        """Check if Git repository exists"""
        return (self.project_root / ".git").exists()
    
    def _get_restore_strategy(self, version_data: Dict[str, Any]) -> str:
        """Determine restore strategy based on version data and Git availability"""
        has_git = self._has_git_repository()
        has_git_info = version_data.get("git_commit") or version_data.get("git_tag")
        
        if has_git and has_git_info:
            return "git+dvc"
        else:
            return "dvc-only"
    
    def _checkout_with_git(self, name: str, tag: str, version_data: Dict[str, Any], 
                          dataset_path: str, dvc_file_path: str, pull: bool, force: bool) -> Dict[str, Any]:
        """Checkout using Git + DVC strategy"""
        try:
            git_tag = version_data.get("git_tag")
            git_commit = version_data.get("git_commit")
            
            if not git_tag and not git_commit:
                return {"error": f"No Git reference found for version {tag}"}
            
            # Use tag if available, otherwise use commit
            git_ref = git_tag if git_tag else git_commit
            
            print(f"🔄 Git checkout: {git_ref}")
            
            # Git checkout
            self.core_ops._run_git_command(["checkout", git_ref], f"Git checkout to {git_ref}")
            
            # DVC checkout (should automatically follow Git)
            print(f"🔄 DVC checkout")
            self.core_ops._run_dvc_command(["checkout"], "DVC checkout")
            
            # DVC pull if requested
            if pull:
                print(f"🔄 DVC pull")
                self.core_ops._run_dvc_command(["pull"], "DVC pull from remote")
            
            return {
                "success": True,
                "dataset": name,
                "version": tag,
                "strategy": "git+dvc",
                "git_reference": git_ref,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Git+DVC checkout failed: {e}"}
    
    def _checkout_without_git(self, name: str, tag: str, version_data: Dict[str, Any], 
                             dataset_path: str, dvc_file_path: str, pull: bool, force: bool) -> Dict[str, Any]:
        """Checkout using DVC-only strategy"""
        try:
            target_hash = version_data["hash"]
            
            print(f"🔄 DVC-only checkout: {target_hash[:8]}...")
            
            # Handle cache directory conflict
            cache_dir = Path(dataset_path) / "cache"
            cache_backup_dir = None
            if cache_dir.exists():
                # Backup cache to central repository before moving
                try:
                    self._export_dataset_cache(dataset_path, previous_version)
                except Exception as export_err:
                    print(f"[yellow]⚠️ Cache export warning: {export_err}[/yellow]")
                print(f"📁 Backing up cache directory to avoid DVC conflict")
                backups_root = Path(self.project_root) / ".ddoc_cache_backups" / name
                backups_root.mkdir(parents=True, exist_ok=True)
                cache_backup_dir = backups_root / datetime.now().strftime('%Y%m%d_%H%M%S')
                # Move entire cache dir outside dataset path
                import shutil
                shutil.move(str(cache_dir), str(cache_backup_dir))
            
            # Update DVC file with target hash
            success = self.version_service.update_dvc_file_hash(dataset_path, target_hash)
            if not success:
                # Restore cache if DVC file update failed
                if cache_backup_dir and cache_backup_dir.exists():
                    cache_backup_dir.rename(cache_dir)
                return {"error": f"Failed to update DVC file hash"}
            
            # DVC checkout
            checkout_args = ["checkout", dvc_file_path]
            if force:
                checkout_args.append("--force")
            self.core_ops._run_dvc_command(checkout_args, "DVC checkout")
            
            # DVC pull if requested
            if pull:
                print(f"🔄 DVC pull")
                self.core_ops._run_dvc_command(["pull", dvc_file_path], "DVC pull from remote")
            
            # Restore cache directory if it was backed up
            if cache_backup_dir and cache_backup_dir.exists():
                import shutil
                if force:
                    print(f"⚠️ Force checkout used - keeping backup cache at {cache_backup_dir}")
                    # Keep backup and create new cache directory (fresh cache)
                    cache_dir.mkdir(exist_ok=True)
                else:
                    print(f"📁 Restoring cache directory from backup")
                    # If destination exists for any reason, remove it first
                    if cache_dir.exists():
                        shutil.rmtree(cache_dir, ignore_errors=True)
                    shutil.move(str(cache_backup_dir), str(cache_dir))

            # Import cache for the target version from central repository
            try:
                self._import_dataset_cache(dataset_path, tag)
            except Exception as import_err:
                print(f"[yellow]⚠️ Cache import warning: {import_err}[/yellow]")
            
            # Check cache existence for this version
            if cache_dir.exists():
                cache_files = list(cache_dir.glob("*"))
                print(f"📁 Cache directory found: {len(cache_files)} files")
                if force:
                    print(f"⚠️ Force checkout used - cache may be outdated")
            else:
                print(f"📁 No cache directory found for this version")
            
            return {
                "success": True,
                "dataset": name,
                "version": tag,
                "strategy": "dvc-only",
                "target_hash": target_hash,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"DVC-only checkout failed: {e}"}
    
    
    def _export_dataset_cache(self, dataset_path: str, version: Optional[str]) -> None:
        if not version:
            return
        try:
            from ddoc_plugin_vision.cache_utils import export_local_cache_to_repository
        except ImportError:
            return
        export_local_cache_to_repository(dataset_path, version)

    def _import_dataset_cache(self, dataset_path: str, version: Optional[str]) -> None:
        if not version:
            return
        try:
            from ddoc_plugin_vision.cache_utils import (
                import_repository_cache_to_local,
                repository_has_cache,
            )
        except ImportError:
            return

        has_attribute = repository_has_cache(dataset_path, version, "attribute_analysis")
        has_embedding = repository_has_cache(dataset_path, version, "embedding_analysis")
        if not has_attribute and not has_embedding:
            return

        import_repository_cache_to_local(dataset_path, version)


    def _create_dvcignore_file(self, dataset_path: Path) -> None:
        """Create .dvcignore file in current working directory to exclude cache and temporary files"""
        try:
            # Create .dvcignore in the current working directory (where ddoc is executed)
            dvcignore_path = self.project_root / ".dvcignore"
            
            # Define content to add to .dvcignore
            dvcignore_content = """# DVC ignore file - exclude cache directories and temporary files from DVC tracking
cache/
**/cache/
/.ddoc_cache_backups/
*.cache
*.tmp
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
.pytest_cache/
.coverage
htmlcov/
.tox/
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.DS_Store
.vscode/
.idea/
*.swp
*.swo
*~
# Analysis output directories
analysis/
plots/
reports/
models/
checkpoints/
logs/
"""
            
            # Check if .dvcignore already exists
            if dvcignore_path.exists():
                # Read existing content
                with open(dvcignore_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                
                # Check if our content is already present
                if "cache/" in existing_content and "analysis/" in existing_content:
                    print(f"   📄 .dvcignore already contains required content in {self.project_root}")
                    return
                
                # Append our content to existing file
                with open(dvcignore_path, 'a', encoding='utf-8') as f:
                    f.write("\n" + dvcignore_content)
                print(f"   📄 Updated .dvcignore in {self.project_root}")
            else:
                # Create new .dvcignore file
                with open(dvcignore_path, 'w', encoding='utf-8') as f:
                    f.write(dvcignore_content)
                print(f"   📄 Created .dvcignore in {self.project_root}")
            
        except Exception as e:
            print(f"[yellow]Warning: Could not create .dvcignore file: {e}[/yellow]")


# Global dataset service instance
_dataset_service = None


def get_dataset_service(project_root: str = ".") -> DatasetService:
    """Get global dataset service instance"""
    global _dataset_service
    if _dataset_service is None:
        _dataset_service = DatasetService(project_root)
    return _dataset_service
