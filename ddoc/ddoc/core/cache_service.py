"""
Cache management service for ddoc snapshots
Data hash-based cache storage with SQLite indexing
"""
import json
import pickle
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .schemas import FileMetadata, AnalysisCache, CacheSummary


class CacheService:
    """Service for managing analysis caches with data hash-based storage"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.cache_dir = self.project_root / ".ddoc" / "cache"
        self.data_dir = self.cache_dir / "data"
        self.index_db = self.cache_dir / "index.db"
        self.workspace_state_file = self.cache_dir / "workspace_state.json"
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite index
        self._init_index()
    
    def _init_index(self):
        """Initialize SQLite index database"""
        conn = sqlite3.connect(self.index_db)
        cursor = conn.cursor()
        
        # Snapshot to data hash mapping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshot_mapping (
                snapshot_id TEXT PRIMARY KEY,
                data_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Data hash cache information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_cache (
                data_hash TEXT PRIMARY KEY,
                cache_types TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_accessed TEXT,
                size_bytes INTEGER,
                file_count INTEGER
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_hash ON snapshot_mapping(data_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON data_cache(created_at)")
        
        conn.commit()
        conn.close()
    
    def get_data_hash_dir(self, data_hash: str) -> Path:
        """Get directory path for a data hash"""
        return self.data_dir / data_hash
    
    def _get_workspace_state(self) -> Dict[str, Any]:
        """Get current workspace state (tracked data_hash)"""
        if not self.workspace_state_file.exists():
            return {"current_data_hash": None}
        
        try:
            with open(self.workspace_state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"current_data_hash": None}
    
    def _update_workspace_state(self, data_hash: str):
        """Update workspace state tracking"""
        with open(self.workspace_state_file, 'w') as f:
            json.dump({
                "current_data_hash": data_hash,
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
    
    def sync_workspace_cache(self, new_data_hash: str, old_data_hash: Optional[str] = None) -> Dict[str, Any]:
        """
        Sync workspace cache when data changes
        
        Args:
            new_data_hash: New data hash after changes
            old_data_hash: Previous data hash (if known, otherwise auto-detected)
            
        Returns:
            Result dictionary with sync status
        """
        if not old_data_hash:
            workspace_state = self._get_workspace_state()
            old_data_hash = workspace_state.get("current_data_hash")
        
        result = {"synced": False, "reason": "no_change"}
        
        if old_data_hash and old_data_hash != new_data_hash:
            # Check if cache exists for old hash
            old_cache_dir = self.get_data_hash_dir(old_data_hash)
            new_cache_dir = self.get_data_hash_dir(new_data_hash)
            
            # Check if new cache already exists
            if new_cache_dir.exists():
                result = {"synced": False, "reason": "new_cache_exists"}
            elif old_cache_dir.exists():
                # Copy cache from old to new hash
                copy_result = self.copy_cache(old_data_hash, new_data_hash)
                
                if copy_result["success"]:
                    result = {
                        "synced": True,
                        "reason": "cache_copied",
                        "cache_types": copy_result.get("cache_types", []),
                        "old_hash": old_data_hash[:8],
                        "new_hash": new_data_hash[:8]
                    }
                else:
                    result = {
                        "synced": False,
                        "reason": "copy_failed",
                        "error": copy_result.get("error")
                    }
            else:
                result = {"synced": False, "reason": "no_old_cache"}
        
        # Update workspace state
        self._update_workspace_state(new_data_hash)
        
        return result
    
    def save_analysis_cache(
        self,
        snapshot_id: str,
        data_hash: str,
        cache_type: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save analysis cache (data hash-based)
        
        Args:
            snapshot_id: Snapshot ID
            data_hash: Data hash from DVC
            cache_type: Type of cache ("summary", "embedding", "attributes", "file_metadata")
            data: Cache data to save
            metadata: Optional metadata
            
        Returns:
            Result dictionary
        """
        try:
            data_dir = self.get_data_hash_dir(data_hash)
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Save based on cache type (support namespaced types like attributes_image, embedding_text, etc.)
            # JSON types: summary, attributes*, file_metadata
            # PKL types: embedding*, xai*
            if cache_type in ["summary", "file_metadata"] or cache_type.startswith("attributes_"):
                cache_file = data_dir / f"{cache_type}.json"
                with open(cache_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
            elif cache_type.startswith("embedding_") or cache_type.startswith("xai_"):
                cache_file = data_dir / f"{cache_type}.pkl"
                with open(cache_file, 'wb') as f:
                    pickle.dump(data, f)
            # Legacy support for non-namespaced types
            elif cache_type in ["attributes", "embedding", "xai"]:
                if cache_type == "attributes":
                    cache_file = data_dir / f"{cache_type}.json"
                    with open(cache_file, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                else:  # embedding or xai
                    cache_file = data_dir / f"{cache_type}.pkl"
                    with open(cache_file, 'wb') as f:
                        pickle.dump(data, f)
            else:
                return {"success": False, "error": f"Unknown cache type: {cache_type}"}
            
            # Save metadata if provided
            if metadata:
                meta_file = data_dir / f"{cache_type}_meta.json"
                with open(meta_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            # Save snapshot mapping
            self._save_snapshot_mapping(snapshot_id, data_hash)
            
            # Update index
            self._update_index(data_hash, cache_type)
            
            return {
                "success": True,
                "cache_file": str(cache_file.relative_to(self.project_root)),
                "data_hash": data_hash
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to save cache: {str(e)}"
            }
    
    def load_analysis_cache(
        self,
        snapshot_id: Optional[str] = None,
        data_hash: Optional[str] = None,
        cache_type: str = "summary"
    ) -> Optional[Any]:
        """
        Load analysis cache
        
        Args:
            snapshot_id: Snapshot ID (optional if data_hash provided)
            data_hash: Data hash (optional if snapshot_id provided)
            cache_type: Type of cache to load
            
        Returns:
            Cache data or None
        """
        # Special handling for workspace - use current data_hash from workspace state
        if snapshot_id == "workspace" and not data_hash:
            workspace_state = self._get_workspace_state()
            data_hash = workspace_state.get("current_data_hash")
            if not data_hash:
                return None
        
        # Resolve data hash from snapshot_id if needed
        if snapshot_id and not data_hash and snapshot_id != "workspace":
            data_hash = self._get_data_hash_by_snapshot(snapshot_id)
            if not data_hash:
                return None
        
        if not data_hash:
            return None
        
        data_dir = self.get_data_hash_dir(data_hash)
        
        # Load based on cache type (support namespaced types)
        # JSON types: summary, attributes*, file_metadata
        # PKL types: embedding*, xai*
        if cache_type in ["summary", "file_metadata"] or cache_type.startswith("attributes_"):
            cache_file = data_dir / f"{cache_type}.json"
            if not cache_file.exists():
                return None
            with open(cache_file, 'r') as f:
                return json.load(f)
        elif cache_type.startswith("embedding_") or cache_type.startswith("xai_"):
            cache_file = data_dir / f"{cache_type}.pkl"
            if not cache_file.exists():
                return None
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        # Legacy support for non-namespaced types
        elif cache_type in ["attributes", "embedding", "xai"]:
            if cache_type == "attributes":
                cache_file = data_dir / f"{cache_type}.json"
            else:  # embedding or xai
                cache_file = data_dir / f"{cache_type}.pkl"
            if not cache_file.exists():
                return None
            if cache_type == "attributes":
                with open(cache_file, 'r') as f:
                    return json.load(f)
            else:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        
        return None
    
    def find_attribute_caches(
        self,
        snapshot_id: Optional[str] = None,
        data_hash: Optional[str] = None,
    ) -> dict:
        """Return all ``attributes*`` JSON caches available for the data
        hash, keyed by their cache_type.

        Plugins write modality-suffixed caches such as
        ``attributes_timeseries.json`` / ``attributes_image.json``.
        Callers (notably ``ddoc analyze drift``) used to look up the
        bare ``attributes`` cache only, which silently missed every
        modality-aware plugin's output. This helper resolves the right
        directory once and lists every variant on disk.

        Returns ``{}`` when no data hash can be resolved or no
        attributes cache exists.
        """
        if snapshot_id == "workspace" and not data_hash:
            workspace_state = self._get_workspace_state()
            data_hash = workspace_state.get("current_data_hash")
        if snapshot_id and not data_hash and snapshot_id != "workspace":
            data_hash = self._get_data_hash_by_snapshot(snapshot_id)
        if not data_hash:
            return {}

        data_dir = self.get_data_hash_dir(data_hash)
        if not data_dir.exists():
            return {}

        out: dict = {}
        for f in data_dir.iterdir():
            if not (f.is_file() and f.suffix == ".json"):
                continue
            stem = f.stem
            if stem == "attributes" or stem.startswith("attributes_"):
                try:
                    with open(f, "r") as fh:
                        out[stem] = json.load(fh)
                except (OSError, json.JSONDecodeError):
                    continue
        return out

    def _save_snapshot_mapping(self, snapshot_id: str, data_hash: str):
        """Save snapshot to data hash mapping (SQLite only)"""
        conn = sqlite3.connect(self.index_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO snapshot_mapping 
            (snapshot_id, data_hash, created_at)
            VALUES (?, ?, ?)
        """, (snapshot_id, data_hash, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def _get_data_hash_by_snapshot(self, snapshot_id: str) -> Optional[str]:
        """Get data hash for a snapshot ID (from SQLite)"""
        conn = sqlite3.connect(self.index_db)
        cursor = conn.cursor()
        cursor.execute("SELECT data_hash FROM snapshot_mapping WHERE snapshot_id = ?", (snapshot_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def copy_cache(self, from_data_hash: str, to_data_hash: str) -> Dict[str, Any]:
        """
        Copy cache from one data hash to another
        
        Args:
            from_data_hash: Source data hash
            to_data_hash: Target data hash
            
        Returns:
            Result dictionary with copy status
        """
        try:
            from_dir = self.get_data_hash_dir(from_data_hash)
            to_dir = self.get_data_hash_dir(to_data_hash)
            
            if not from_dir.exists():
                return {
                    "success": False,
                    "error": f"Source cache not found: {from_data_hash}"
                }
            
            # Create target directory
            to_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all cache files
            import shutil
            copied_files = []
            for cache_file in from_dir.iterdir():
                if cache_file.is_file():
                    dest_file = to_dir / cache_file.name
                    shutil.copy2(cache_file, dest_file)
                    copied_files.append(cache_file.name)
            
            # Update index
            conn = sqlite3.connect(self.index_db)
            cursor = conn.cursor()
            
            # Get cache types from source (support namespaced types)
            cache_types = []
            for cache_file in from_dir.iterdir():
                if cache_file.is_file():
                    name = cache_file.name
                    if name == "summary.json":
                        cache_types.append("summary")
                    elif name == "file_metadata.json":
                        cache_types.append("file_metadata")
                    elif name.startswith("attributes") and name.endswith(".json"):
                        # Extract cache type: attributes_image.json -> attributes_image
                        cache_type = name[:-5]  # Remove .json
                        if cache_type not in cache_types:
                            cache_types.append(cache_type)
                    elif name.startswith("embedding") and name.endswith(".pkl"):
                        # Extract cache type: embedding_image.pkl -> embedding_image
                        cache_type = name[:-4]  # Remove .pkl
                        if cache_type not in cache_types:
                            cache_types.append(cache_type)
                    elif name.startswith("xai") and name.endswith(".pkl"):
                        # Extract cache type: xai_image.pkl -> xai_image
                        cache_type = name[:-4]  # Remove .pkl
                        if cache_type not in cache_types:
                            cache_types.append(cache_type)
            
            # Update data_cache table for target hash
            cursor.execute("""
                INSERT OR REPLACE INTO data_cache 
                (data_hash, cache_types, created_at, last_accessed, size_bytes, file_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                to_data_hash,
                json.dumps(cache_types),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                sum(f.stat().st_size for f in to_dir.rglob('*') if f.is_file()) if to_dir.exists() else 0,
                len(list(to_dir.rglob('*'))) if to_dir.exists() else 0
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "copied_files": copied_files,
                "cache_types": cache_types
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to copy cache: {str(e)}"
            }
    
    def find_snapshots_by_data_hash(self, data_hash: str) -> List[str]:
        """Find all snapshots with the same data hash"""
        conn = sqlite3.connect(self.index_db)
        cursor = conn.cursor()
        cursor.execute("SELECT snapshot_id FROM snapshot_mapping WHERE data_hash = ?", (data_hash,))
        results = cursor.fetchall()
        conn.close()
        
        return [r[0] for r in results]
    
    def _update_index(self, data_hash: str, cache_type: str):
        """Update SQLite index"""
        conn = sqlite3.connect(self.index_db)
        cursor = conn.cursor()
        
        # Check existing cache types
        cursor.execute("SELECT cache_types FROM data_cache WHERE data_hash = ?", (data_hash,))
        result = cursor.fetchone()
        
        if result:
            # Update existing
            cache_types = json.loads(result[0])
            if cache_type not in cache_types:
                cache_types.append(cache_type)
                cursor.execute("""
                    UPDATE data_cache 
                    SET cache_types = ?, last_accessed = ?
                    WHERE data_hash = ?
                """, (json.dumps(cache_types), datetime.now().isoformat(), data_hash))
        else:
            # Insert new
            data_dir = self.get_data_hash_dir(data_hash)
            size_bytes = sum(f.stat().st_size for f in data_dir.rglob('*') if f.is_file()) if data_dir.exists() else 0
            file_count = len(list(data_dir.rglob('*'))) if data_dir.exists() else 0
            
            cursor.execute("""
                INSERT INTO data_cache 
                (data_hash, cache_types, created_at, last_accessed, size_bytes, file_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data_hash,
                json.dumps([cache_type]),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                size_bytes,
                file_count
            ))
        
        conn.commit()
        conn.close()
    
    def save_file_metadata(
        self,
        snapshot_id: str,
        data_hash: str,
        file_metadata: Dict[str, FileMetadata]
    ) -> Dict[str, Any]:
        """Save file-level metadata for incremental analysis"""
        try:
            data_dir = self.get_data_hash_dir(data_hash)
            data_dir.mkdir(parents=True, exist_ok=True)
            
            metadata_file = data_dir / "file_metadata.json"
            metadata_dict = {
                k: v.model_dump() if isinstance(v, FileMetadata) else v
                for k, v in file_metadata.items()
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata_dict, f, indent=2)
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def load_file_metadata(
        self,
        snapshot_id: Optional[str] = None,
        data_hash: Optional[str] = None
    ) -> Optional[Dict[str, FileMetadata]]:
        """Load file-level metadata"""
        # Special handling for workspace - use current data_hash from workspace state
        if snapshot_id == "workspace" and not data_hash:
            workspace_state = self._get_workspace_state()
            data_hash = workspace_state.get("current_data_hash")
            if not data_hash:
                return None
        
        if snapshot_id and not data_hash and snapshot_id != "workspace":
            data_hash = self._get_data_hash_by_snapshot(snapshot_id)
        
        if not data_hash:
            return None
        
        metadata_file = self.get_data_hash_dir(data_hash) / "file_metadata.json"
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        
        return {
            k: FileMetadata(**v) if isinstance(v, dict) else v
            for k, v in data.items()
        }
    
    def compute_incremental_changes(
        self,
        snapshot_id: str,
        current_files: Dict[str, Dict[str, Any]]  # {file_path: {size, mtime, hash}}
    ) -> Dict[str, Any]:
        """
        Compute incremental changes for analysis
        
        Args:
            snapshot_id: Snapshot ID
            current_files: Current file information
            
        Returns:
            Dictionary with new_files, modified_files, removed_files, unchanged_files
        """
        # Load file metadata (workspace will use current data_hash from workspace state)
        cached_metadata = self.load_file_metadata(snapshot_id=snapshot_id)
        if not cached_metadata:
            # No cache, all files are new
            return {
                "new_files": list(current_files.keys()),
                "modified_files": [],
                "removed_files": [],
                "unchanged_files": []
            }
        
        new_files = []
        modified_files = []
        unchanged_files = []
        cached_paths = set(cached_metadata.keys())
        current_paths = set(current_files.keys())
        
        # New files
        new_files = list(current_paths - cached_paths)
        
        # Removed files
        removed_files = list(cached_paths - current_paths)
        
        # Check modified/unchanged
        for file_path in current_paths & cached_paths:
            cached = cached_metadata[file_path]
            current = current_files[file_path]
            
            # Check if file changed (size or mtime)
            if (cached.file_size != current.get("size", 0) or 
                abs(cached.file_mtime - current.get("mtime", 0)) > 1.0):
                modified_files.append(file_path)
            else:
                unchanged_files.append(file_path)
        
        return {
            "new_files": new_files,
            "modified_files": modified_files,
            "removed_files": removed_files,
            "unchanged_files": unchanged_files
        }
    
    def get_cache_info(
        self,
        snapshot_id: Optional[str] = None,
        data_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get cache information"""
        if snapshot_id and not data_hash:
            data_hash = self._get_data_hash_by_snapshot(snapshot_id)
        
        if not data_hash:
            return {"error": "No cache found"}
        
        conn = sqlite3.connect(self.index_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM data_cache WHERE data_hash = ?", (data_hash,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {"error": "Cache not found in index"}
        
        snapshots = self.find_snapshots_by_data_hash(data_hash)
        
        return {
            "data_hash": data_hash,
            "cache_types": json.loads(result[1]),
            "created_at": result[2],
            "last_accessed": result[3],
            "size_bytes": result[4],
            "file_count": result[5],
            "snapshots": snapshots,
            "snapshot_count": len(snapshots)
        }
    
    # Legacy methods for backward compatibility
    def save_summary_cache(
        self,
        snapshot_id: str,
        data_hash: str,
        statistics: Dict[str, Any],
        distributions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Legacy method: Save summary cache"""
        return self.save_analysis_cache(
            snapshot_id=snapshot_id,
            data_hash=data_hash,
            cache_type="summary",
            data={
                "statistics": statistics,
                "distributions": distributions
            }
        )
    
    def load_summary_cache(self, snapshot_id: str) -> Optional[CacheSummary]:
        """Legacy method: Load summary cache"""
        data_hash = self._get_data_hash_by_snapshot(snapshot_id)
        if not data_hash:
            return None
        
        cache_data = self.load_analysis_cache(data_hash=data_hash, cache_type="summary")
        if not cache_data:
            return None
        
        return CacheSummary(
            snapshot_id=snapshot_id,
            created_at=datetime.now().isoformat(),
            data_hash=data_hash,
            statistics=cache_data.get("statistics", {}),
            distributions=cache_data.get("distributions", {})
        )
    
    def save_embedding_cache(
        self,
        snapshot_id: str,
        data_hash: str,
        embeddings: Any,
        embedding_summary: Optional[Dict[str, Any]] = None,
        cluster_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Legacy method: Save embedding cache"""
        metadata = {}
        if embedding_summary:
            metadata["embedding_summary"] = embedding_summary
        if cluster_info:
            metadata["cluster_info"] = cluster_info
        
        return self.save_analysis_cache(
            snapshot_id=snapshot_id,
            data_hash=data_hash,
            cache_type="embedding",
            data=embeddings,
            metadata=metadata
        )
    
    def load_embedding_cache(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Legacy method: Load embedding cache"""
        data_hash = self._get_data_hash_by_snapshot(snapshot_id)
        if not data_hash:
            return None
        
        embeddings = self.load_analysis_cache(data_hash=data_hash, cache_type="embedding")
        if embeddings is None:
            return None
        
        metadata = self.load_analysis_cache(data_hash=data_hash, cache_type="embedding_meta")
        
        return {
            "embeddings": embeddings,
            "metadata": metadata or {}
        }
    
    def cache_exists(self, snapshot_id: str, cache_type: str = "summary") -> bool:
        """Check if cache exists"""
        data_hash = self._get_data_hash_by_snapshot(snapshot_id)
        if not data_hash:
            return False
        
        cache = self.load_analysis_cache(data_hash=data_hash, cache_type=cache_type)
        return cache is not None
    
    def delete_cache(self, snapshot_id: str, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """Delete cache for a snapshot"""
        data_hash = self._get_data_hash_by_snapshot(snapshot_id)
        if not data_hash:
            return {"success": False, "error": "Snapshot not found"}
        
        data_dir = self.get_data_hash_dir(data_hash)
        deleted_files = []
        
        if cache_type is None:
            # Delete all cache types
            for cache_file in data_dir.glob("*"):
                if cache_file.is_file():
                    cache_file.unlink()
                    deleted_files.append(str(cache_file.relative_to(self.project_root)))
        else:
            # Delete specific cache type
            cache_file = data_dir / f"{cache_type}.json"
            if not cache_file.exists():
                cache_file = data_dir / f"{cache_type}.pkl"
            if cache_file.exists():
                cache_file.unlink()
                deleted_files.append(str(cache_file.relative_to(self.project_root)))
            
            meta_file = data_dir / f"{cache_type}_meta.json"
            if meta_file.exists():
                meta_file.unlink()
                deleted_files.append(str(meta_file.relative_to(self.project_root)))
        
        return {
            "success": True,
            "deleted_files": deleted_files
        }
    
    def list_caches(self) -> Dict[str, Any]:
        """List all caches"""
        try:
            caches = []
            
            # Get from SQLite index
            conn = sqlite3.connect(self.index_db)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM data_cache")
            results = cursor.fetchall()
            conn.close()
            
            for result in results:
                data_hash = result[0]
                cache_types = json.loads(result[1])
                snapshots = self.find_snapshots_by_data_hash(data_hash)
                
                caches.append({
                    "data_hash": data_hash,
                    "cache_types": cache_types,
                    "created_at": result[2],
                    "last_accessed": result[3],
                    "size_bytes": result[4],
                    "file_count": result[5],
                    "snapshots": snapshots,
                    "snapshot_count": len(snapshots)
                })
            
            return {
                "success": True,
                "caches": caches,
                "count": len(caches)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list caches: {str(e)}"
            }
    
    def compute_drift_from_caches(
        self,
        snapshot_id1: str,
        snapshot_id2: str
    ) -> Dict[str, Any]:
        """Compute drift between two snapshots using cached summaries"""
        try:
            cache1 = self.load_summary_cache(snapshot_id1)
            cache2 = self.load_summary_cache(snapshot_id2)
            
            if not cache1 or not cache2:
                return {
                    "success": False,
                    "error": "One or both caches not found. Run analysis first."
                }
            
            drift_scores = {}
            stats1 = cache1.statistics
            stats2 = cache2.statistics
            
            for key in set(stats1.keys()) | set(stats2.keys()):
                if key in stats1 and key in stats2:
                    try:
                        val1 = float(stats1[key])
                        val2 = float(stats2[key])
                        drift = abs(val2 - val1) / (abs(val1) + 1e-10)
                        drift_scores[key] = {
                            "value1": val1,
                            "value2": val2,
                            "drift_score": drift
                        }
                    except (ValueError, TypeError):
                        pass
            
            return {
                "success": True,
                "snapshot1": snapshot_id1,
                "snapshot2": snapshot_id2,
                "drift_scores": drift_scores,
                "overall_drift": sum(s["drift_score"] for s in drift_scores.values()) / len(drift_scores) if drift_scores else 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to compute drift: {str(e)}"
            }


def get_cache_service(project_root: Optional[str] = None) -> CacheService:
    """Factory function to get cache service instance"""
    return CacheService(project_root)
