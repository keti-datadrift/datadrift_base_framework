"""
Version Service for ddoc - Git-free dataset version management
"""
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich import print


class VersionService:
    """
    Version management service using DVC hash tracking
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.metadata_dir = self.project_root / ".ddoc_metadata"
        self.metadata_dir.mkdir(exist_ok=True)
        
        self.dataset_versions_file = self.metadata_dir / "dataset_versions.json"
        self.experiment_versions_file = self.metadata_dir / "experiment_versions.json"
        
        self.config = self._load_config()
        self._init_version_files()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load version control configuration from params.yaml"""
        params_file = self.project_root / "params.yaml"
        if params_file.exists():
            try:
                with open(params_file, 'r') as f:
                    params = yaml.safe_load(f) or {}
                return params.get('version_control', {
                    'policy': 'strict',
                    'auto_version_prefix': 'auto_',
                    'version_format': 'v{major}.{minor}'
                })
            except Exception as e:
                print(f"[yellow]Warning: Failed to load params.yaml: {e}[/yellow]")
        
        return {
            'policy': 'strict',
            'auto_version_prefix': 'auto_',
            'version_format': 'v{major}.{minor}'
        }
    
    def _init_version_files(self):
        """Initialize version files if they don't exist"""
        if not self.dataset_versions_file.exists():
            with open(self.dataset_versions_file, 'w') as f:
                json.dump({}, f, indent=2)
        
        if not self.experiment_versions_file.exists():
            with open(self.experiment_versions_file, 'w') as f:
                json.dump({}, f, indent=2)
    
    def get_dvc_hash(self, dataset_path: str) -> Optional[str]:
        """Extract MD5 hash from DVC file"""
        try:
            dataset_path = Path(dataset_path)
            dvc_file = dataset_path.with_suffix('.dvc')
            
            if not dvc_file.exists():
                return None
            
            with open(dvc_file, 'r') as f:
                dvc_data = yaml.safe_load(f)
            
            # Extract MD5 hash from DVC file
            if 'outs' in dvc_data and dvc_data['outs']:
                return dvc_data['outs'][0].get('md5')
            
            return None
        except Exception as e:
            print(f"[yellow]Warning: Failed to read DVC hash for {dataset_path}: {e}[/yellow]")
            return None
    
    def create_dataset_version(self, name: str, version: str, message: str = "") -> Dict[str, Any]:
        """Create a new dataset version"""
        try:
            versions_data = self._load_dataset_versions()
            
            # Get dataset path from params.yaml
            dataset_path = self._get_dataset_path(name)
            if not dataset_path:
                return {"error": f"Dataset {name} not found in params.yaml"}
            
            # Get current DVC hash
            current_hash = self.get_dvc_hash(dataset_path)
            if not current_hash:
                return {"error": f"No DVC file found for dataset {name}"}
            
            # Get Git information if available
            git_info = self._get_git_info()
            
            dataset_entry = versions_data.setdefault(name, {
                "versions": {},
                "current_version": None,
                "latest_hash": None,
                "aliases": {}
            })

            # Ensure aliases map exists for legacy data
            dataset_entry.setdefault("aliases", {})
            
            # Create version entry
            version_entry = {
                "hash": current_hash,
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "git_commit": git_info.get("commit"),
                "git_tag": git_info.get("tag"),
                "restore_strategy": git_info.get("strategy", "dvc-only"),
                "metadata": {
                    "dataset_path": str(dataset_path),
                    "created_by": "ddoc"
                },
                "alias": None
            }
            
            dataset_entry["versions"][version] = version_entry
            dataset_entry["current_version"] = version
            dataset_entry["latest_hash"] = current_hash
            # Remove legacy alias mapping for this version if exists
            aliases = dataset_entry.get("aliases", {})
            aliases_to_remove = [alias for alias, ver in aliases.items() if ver == version]
            for alias in aliases_to_remove:
                aliases.pop(alias, None)

            self._save_dataset_versions(versions_data)
            
            print(f"✅ Created version {version} for dataset {name}")
            print(f"   Hash: {current_hash[:8]}...")
            print(f"   Message: {message}")
            
            return {
                "success": True,
                "dataset": name,
                "version": version,
                "hash": current_hash,
                "timestamp": version_entry["timestamp"],
                "message": message,
                "alias": version_entry.get("alias")
            }
            
        except Exception as e:
            return {"error": f"Failed to create version: {e}"}
    
    def get_dataset_version_history(self, name: str) -> List[Dict[str, Any]]:
        """Get version history for a dataset"""
        try:
            versions_data = self._load_dataset_versions()
            
            if name not in versions_data:
                return []
            
            versions = []
            for version, data in versions_data[name]["versions"].items():
                versions.append({
                    "version": version,
                    "hash": data["hash"],
                    "timestamp": data["timestamp"],
                    "message": data["message"],
                    "metadata": data.get("metadata", {}),
                    "alias": data.get("alias")
                })
            
            # Sort by timestamp (newest first)
            versions.sort(key=lambda x: x["timestamp"], reverse=True)
            return versions
            
        except Exception as e:
            return [{"error": f"Failed to get version history: {e}"}]
    
    def get_dataset_status(self, name: str) -> Dict[str, Any]:
        """Get dataset version status (clean/modified/unversioned)"""
        try:
            versions_data = self._load_dataset_versions()
            
            if name not in versions_data:
                return {
                    "state": "unversioned",
                    "current_version": None,
                    "latest_hash": None,
                    "changes": "Dataset not versioned"
                }
            
            # Get current DVC hash
            dataset_path = self._get_dataset_path(name)
            if not dataset_path:
                return {
                    "state": "error",
                    "current_version": None,
                    "latest_hash": None,
                    "changes": "Dataset not found in params.yaml"
                }
            
            current_hash = self.get_dvc_hash(dataset_path)
            if not current_hash:
                return {
                    "state": "error",
                    "current_version": None,
                    "latest_hash": None,
                    "changes": "No DVC file found"
                }
            
            latest_hash = versions_data[name]["latest_hash"]
            current_version = versions_data[name]["current_version"]
            
            if current_hash == latest_hash:
                return {
                    "state": "clean",
                    "current_version": current_version,
                    "latest_hash": current_hash,
                    "changes": None,
                    "alias": versions_data[name]["versions"].get(current_version, {}).get("alias")
                }
            else:
                return {
                    "state": "modified",
                    "current_version": current_version,
                    "latest_hash": latest_hash,
                    "current_hash": current_hash,
                    "changes": f"Hash changed from {latest_hash[:8]}... to {current_hash[:8]}...",
                    "alias": versions_data[name]["versions"].get(current_version, {}).get("alias")
                }
                
        except Exception as e:
            return {
                "state": "error",
                "current_version": None,
                "latest_hash": None,
                "changes": f"Error checking status: {e}"
            }
    
    def check_version_state(self, name: str) -> bool:
        """Check if dataset version state allows operations (Strict mode)"""
        status = self.get_dataset_status(name)
        
        if status["state"] == "unversioned":
            if self.config["policy"] == "strict":
                raise ValueError(f"Dataset {name} is not versioned. Run 'ddoc dataset version {name}' first.")
            elif self.config["policy"] == "warning":
                print(f"[yellow]Warning: Dataset {name} is not versioned. Results may not be reproducible.[/yellow]")
            elif self.config["policy"] == "auto":
                # Auto-create version
                auto_version = f"{self.config['auto_version_prefix']}{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.create_dataset_version(name, auto_version, "Auto-generated version")
                print(f"[green]Auto-created version {auto_version} for dataset {name}[/green]")
        
        elif status["state"] == "modified":
            if self.config["policy"] == "strict":
                raise ValueError(f"Dataset {name} has uncommitted changes. Run 'ddoc dataset version {name}' first.")
            elif self.config["policy"] == "warning":
                print(f"[yellow]Warning: Dataset {name} has uncommitted changes. Results may not be reproducible.[/yellow]")
            elif self.config["policy"] == "auto":
                # Auto-create version
                auto_version = f"{self.config['auto_version_prefix']}{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.create_dataset_version(name, auto_version, "Auto-generated version for changes")
                print(f"[green]Auto-created version {auto_version} for dataset {name}[/green]")
        
        return True
    
    def generate_next_version(self, name: str) -> str:
        """Generate next version number for dataset"""
        try:
            versions = self.get_dataset_version_history(name)
            
            if not versions:
                return "v1.0"
            
            # Find highest version number
            max_major = 0
            max_minor = 0
            
            for version_info in versions:
                version = version_info["version"]
                if version.startswith("v") and "." in version:
                    try:
                        major, minor = version[1:].split(".")
                        major = int(major)
                        minor = int(minor)
                        
                        if major > max_major or (major == max_major and minor > max_minor):
                            max_major = major
                            max_minor = minor
                    except ValueError:
                        continue
            
            # Increment minor version
            return f"v{max_major}.{max_minor + 1}"
            
        except Exception:
            return "v1.0"

    def list_dataset_versions(self, name: str) -> List[Dict[str, Any]]:
        """List dataset versions with alias metadata"""
        versions = self.get_dataset_version_history(name)
        versions.sort(key=lambda x: x["timestamp"], reverse=True)
        return versions

    def set_dataset_version_alias(self, name: str, version: str, alias: Optional[str]) -> Dict[str, Any]:
        """Set or remove alias for a specific dataset version"""
        versions_data = self._load_dataset_versions()

        if name not in versions_data or version not in versions_data[name]["versions"]:
            return {"success": False, "error": f"Version {version} not found for dataset {name}"}

        dataset_entry = versions_data[name]
        dataset_entry.setdefault("aliases", {})

        # Normalize empty alias to None
        alias = alias.strip() if isinstance(alias, str) else alias
        if alias == "":
            alias = None

        if alias:
            # Ensure alias not already used for another version
            current_alias_owner = dataset_entry["aliases"].get(alias)
            if current_alias_owner and current_alias_owner != version:
                return {"success": False, "error": f"Alias '{alias}' is already used by version {current_alias_owner}"}

            # Remove existing alias mapping for this version
            self._remove_alias_mapping(dataset_entry, version)

            dataset_entry["aliases"][alias] = version
            dataset_entry["versions"][version]["alias"] = alias
        else:
            # Remove alias for this version
            self._remove_alias_mapping(dataset_entry, version)
            dataset_entry["versions"][version]["alias"] = None

        self._save_dataset_versions(versions_data)

        return {
            "success": True,
            "dataset": name,
            "version": version,
            "alias": dataset_entry["versions"][version].get("alias")
        }

    def get_dataset_version_by_alias(self, name: str, alias: str) -> Optional[str]:
        """Return version identifier for the given alias"""
        versions_data = self._load_dataset_versions()
        dataset_entry = versions_data.get(name)
        if not dataset_entry:
            return None
        dataset_entry.setdefault("aliases", {})
        return dataset_entry["aliases"].get(alias)

    def _remove_alias_mapping(self, dataset_entry: Dict[str, Any], version: str) -> None:
        """Remove alias mapping associated with a version"""
        aliases = dataset_entry.setdefault("aliases", {})
        to_remove = [alias for alias, ver in aliases.items() if ver == version]
        for alias in to_remove:
            aliases.pop(alias, None)

    def _load_dataset_versions(self) -> Dict[str, Any]:
        with open(self.dataset_versions_file, 'r') as f:
            return json.load(f)

    def _save_dataset_versions(self, data: Dict[str, Any]) -> None:
        with open(self.dataset_versions_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_experiment_version(self, dataset_name: str, dataset_version: str, exp_name: str) -> str:
        """Create experiment version for specific dataset version"""
        try:
            with open(self.experiment_versions_file, 'r') as f:
                exp_versions = json.load(f)
            
            dataset_key = f"{dataset_name}@{dataset_version}"
            
            if dataset_key not in exp_versions:
                exp_versions[dataset_key] = {
                    "experiments": {},
                    "counter": 0
                }
            
            exp_versions[dataset_key]["counter"] += 1
            exp_counter = exp_versions[dataset_key]["counter"]
            
            exp_version = f"exp_{exp_counter}"
            
            exp_versions[dataset_key]["experiments"][exp_version] = {
                "exp_name": exp_name,
                "timestamp": datetime.now().isoformat(),
                "metadata": {}
            }
            
            with open(self.experiment_versions_file, 'w') as f:
                json.dump(exp_versions, f, indent=2)
            
            return exp_version
            
        except Exception as e:
            print(f"[yellow]Warning: Failed to create experiment version: {e}[/yellow]")
            return f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _get_dataset_path(self, name: str) -> Optional[str]:
        """Get dataset path from dataset mappings or params.yaml"""
        try:
            # First try the new mapping system
            from .metadata_service import get_metadata_service
            metadata_service = get_metadata_service(str(self.project_root))
            mapping = metadata_service.get_dataset_mapping(name)
            if mapping:
                return mapping.get('dataset_path')
            
            # Fallback to params.yaml (legacy support)
            params_file = self.project_root / "params.yaml"
            if not params_file.exists():
                return None
            
            with open(params_file, 'r') as f:
                params = yaml.safe_load(f) or {}
            
            datasets = params.get('datasets', [])
            for dataset in datasets:
                if dataset.get('name') == name:
                    return dataset.get('path')
            
            return None
            
        except Exception:
            return None
    
    def _get_git_info(self) -> Dict[str, Any]:
        """Get Git information if available"""
        git_info = {
            "commit": None,
            "tag": None,
            "strategy": "dvc-only"
        }
        
        try:
            # Check if Git repository exists
            git_dir = self.project_root / ".git"
            if not git_dir.exists():
                return git_info
            
            # Get current commit hash
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            git_info["commit"] = result.stdout.strip()
            
            # Check if we're on a tag
            try:
                tag_result = subprocess.run(
                    ["git", "describe", "--tags", "--exact-match", "HEAD"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                git_info["tag"] = tag_result.stdout.strip()
            except subprocess.CalledProcessError:
                # Not on a tag, that's fine
                pass
            
            # Set strategy based on Git availability
            if git_info["commit"]:
                git_info["strategy"] = "git+dvc"
            
        except Exception as e:
            print(f"[yellow]Warning: Could not get Git info: {e}[/yellow]")
        
        return git_info
    
    def update_dvc_file_hash(self, dataset_path: str, target_hash: str) -> bool:
        """Update DVC file with target hash for checkout"""
        try:
            dvc_file = Path(dataset_path).with_suffix('.dvc')
            
            if not dvc_file.exists():
                raise Exception(f"DVC file not found: {dvc_file}")
            
            # DVC 파일 읽기
            with open(dvc_file, 'r') as f:
                dvc_data = yaml.safe_load(f)
            
            # 해시 업데이트
            if 'outs' in dvc_data and dvc_data['outs']:
                old_hash = dvc_data['outs'][0].get('md5', 'unknown')
                dvc_data['outs'][0]['md5'] = target_hash
                
                # DVC 파일 저장
                with open(dvc_file, 'w') as f:
                    yaml.safe_dump(dvc_data, f, default_flow_style=False)
                
                print(f"✅ Updated DVC file hash: {old_hash[:8]}... → {target_hash[:8]}...")
                return True
            else:
                raise Exception("Invalid DVC file structure")
                
        except Exception as e:
            print(f"❌ Failed to update DVC file hash: {e}")
            return False


# Global version service instance
_version_service = None


def get_version_service(project_root: str = ".") -> VersionService:
    """Get global version service instance"""
    global _version_service
    if _version_service is None:
        _version_service = VersionService(project_root)
    return _version_service
