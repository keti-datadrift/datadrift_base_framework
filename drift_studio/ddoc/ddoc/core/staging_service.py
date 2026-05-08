"""
Staging Service for ddoc - Git-like staging area for dataset changes
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich import print


class StagingService:
    """
    Staging service for managing dataset changes before commit
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.metadata_dir = self.project_root / ".ddoc_metadata"
        self.metadata_dir.mkdir(exist_ok=True)
        
        self.staging_file = self.metadata_dir / "staging.json"
        self._init_staging()
    
    def _empty_staging(self) -> Dict[str, Any]:
        return {
            'staged_datasets': {},
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
        }

    def _init_staging(self) -> Dict[str, Any]:
        """Initialize staging file if missing; return the in-memory shape.

        Round-7 — previously returned None, which broke the
        ``return self._init_staging()`` fallback in ``_load_staging``
        whenever the staging file got deleted (e.g. the test suite
        reusing a singleton across tmpdirs).
        """
        staging = self._empty_staging()
        if not self.staging_file.exists():
            self.metadata_dir.mkdir(parents=True, exist_ok=True)
            self._save_staging(staging)
        return staging

    def _load_staging(self) -> Dict[str, Any]:
        """Load staging data — always returns a usable dict."""
        if self.staging_file.exists():
            try:
                with open(self.staging_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError, OSError):
                print("[yellow]Warning: Could not load staging data, starting fresh[/yellow]")
                return self._empty_staging()
        return self._init_staging()
    
    def _save_staging(self, staging_data: Dict[str, Any]):
        """Save staging data"""
        staging_data['last_updated'] = datetime.now().isoformat()
        with open(self.staging_file, 'w') as f:
            json.dump(staging_data, f, indent=2)
    
    def stage_dataset(
        self,
        name: str,
        path: str,
        operation: str,
        formats: List[str] = None,
        config: str = None,
        current_hash: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Stage a dataset for commit
        
        Args:
            name: Dataset name
            path: Dataset path
            operation: "new" or "modified"
            formats: File formats (optional)
            config: Config file (optional)
            current_hash: Current DVC hash (optional)
            metadata: Additional metadata (optional)
        
        Returns:
            Result dictionary with success status
        """
        try:
            staging = self._load_staging()
            
            staging['staged_datasets'][name] = {
                'operation': operation,
                'path': path,
                'formats': formats or [],
                'config': config,
                'current_hash': current_hash,
                'staged_at': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            self._save_staging(staging)
            
            return {
                'success': True,
                'dataset': name,
                'operation': operation,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to stage dataset: {e}"
            }
    
    def unstage_dataset(self, name: str) -> Dict[str, Any]:
        """
        Remove a dataset from staging area
        
        Args:
            name: Dataset name to unstage
        
        Returns:
            Result dictionary with success status
        """
        try:
            staging = self._load_staging()
            
            if name not in staging['staged_datasets']:
                return {
                    'success': False,
                    'error': f"Dataset {name} is not staged"
                }
            
            del staging['staged_datasets'][name]
            self._save_staging(staging)
            
            return {
                'success': True,
                'dataset': name,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to unstage dataset: {e}"
            }
    
    def get_staged_changes(self) -> Dict[str, Any]:
        """
        Get all staged changes
        
        Returns:
            Dictionary with staged datasets categorized by operation
        """
        try:
            staging = self._load_staging()
            
            new_datasets = []
            modified_datasets = []
            
            for name, info in staging['staged_datasets'].items():
                dataset_info = {
                    'name': name,
                    'path': info.get('path'),
                    'current_hash': info.get('current_hash'),
                    'staged_at': info.get('staged_at'),
                    'formats': info.get('formats', []),
                    'config': info.get('config'),
                    'metadata': info.get('metadata', {})
                }
                
                if info.get('operation') == 'new':
                    new_datasets.append(dataset_info)
                elif info.get('operation') == 'modified':
                    modified_datasets.append(dataset_info)
            
            return {
                'success': True,
                'new': new_datasets,
                'modified': modified_datasets,
                'total': len(new_datasets) + len(modified_datasets)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to get staged changes: {e}",
                'new': [],
                'modified': [],
                'total': 0
            }
    
    def clear_staging(self) -> Dict[str, Any]:
        """
        Clear all staging area (typically after successful commit)
        
        Returns:
            Result dictionary with success status
        """
        try:
            staging = {
                'staged_datasets': {},
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            self._save_staging(staging)
            
            return {
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to clear staging: {e}"
            }
    
    def is_staged(self, name: str) -> bool:
        """
        Check if a dataset is staged
        
        Args:
            name: Dataset name
        
        Returns:
            True if dataset is staged, False otherwise
        """
        try:
            staging = self._load_staging()
            return name in staging['staged_datasets']
        except Exception:
            return False
    
    def get_staged_dataset(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get staging information for a specific dataset
        
        Args:
            name: Dataset name
        
        Returns:
            Staged dataset info or None if not staged
        """
        try:
            staging = self._load_staging()
            return staging['staged_datasets'].get(name)
        except Exception:
            return None


# Global staging service instance
_staging_service = None


def get_staging_service(project_root: str = ".") -> StagingService:
    """Return a staging service for ``project_root``.

    Round-7 — was a singleton that ignored ``project_root`` on every
    call after the first, which left subsequent callers (notably
    tests using fresh tmpdirs) pointing at a deleted metadata
    directory. Now we cache by ``project_root`` so repeated calls
    with the same root are still cheap, but a different root gets a
    fresh instance.
    """
    global _staging_service
    cur = _staging_service
    if cur is None or str(Path(project_root).resolve()) != str(cur.project_root.resolve()):
        _staging_service = StagingService(project_root)
    return _staging_service

