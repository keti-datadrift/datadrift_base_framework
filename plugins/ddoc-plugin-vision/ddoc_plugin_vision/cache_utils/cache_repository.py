"""Central cache repository utilities for versioned analysis data.

This module enables storing and retrieving version-specific analysis caches
outside of the dataset directory so that multiple dataset versions can
coexist without clobbering one another. The repository stores pickle-based
cache payloads along with simple JSON metadata records.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


class CacheRepository:
    """Version-aware cache repository rooted at ``.ddoc_cache_store``.

    The repository layout is:

    ``<project_root>/.ddoc_cache_store/<dataset_name>/<version>/``

    Each version directory stores ``{data_type}.cache`` pickle files and
    ``{data_type}_meta.json`` metadata describing the stored payload.
    """

    STORE_DIRNAME = ".ddoc_cache_store"

    def __init__(self, project_root: Path, dataset_name: str) -> None:
        self.project_root = Path(project_root).resolve()
        self.dataset_name = dataset_name
        self.root_dir = self.project_root / self.STORE_DIRNAME / dataset_name
        self.root_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_directory(cls, dataset_directory: str | Path, dataset_name: Optional[str] = None) -> "CacheRepository":
        dataset_path = Path(dataset_directory).resolve()
        if dataset_name is None:
            dataset_name = dataset_path.name
        project_root = cls._discover_project_root(dataset_path)
        return cls(project_root, dataset_name)

    @staticmethod
    def _discover_project_root(start_path: Path) -> Path:
        """Heuristically find the project root for the given dataset path."""

        markers = {".ddoc_metadata", "params.yaml", ".git"}
        for candidate in [start_path] + list(start_path.parents):
            if any((candidate / marker).exists() for marker in markers):
                return candidate
        # Fallback to current working directory if no marker is found.
        return Path.cwd().resolve()

    # ------------------------------------------------------------------
    # Public repository operations
    # ------------------------------------------------------------------
    def save(self, version: str, data_type: str, content: Any) -> Path:
        """Persist cache content for the provided version and data type."""

        version_dir = self._ensure_version_dir(version)
        cache_path = version_dir / f"{data_type}.cache"
        metadata_path = version_dir / f"{data_type}_meta.json"

        with open(cache_path, "wb") as fh:
            pickle.dump(content, fh)

        file_size = cache_path.stat().st_size
        metadata = {
            "created_time": datetime.now().isoformat(),
            "content_type": "pickle",
            "file_size": file_size,
            "dataset": self.dataset_name,
            "version": version,
            "data_type": data_type,
        }

        with open(metadata_path, "w") as fh:
            json.dump(metadata, fh, indent=2)

        return cache_path

    def load(self, version: str, data_type: str) -> Optional[Any]:
        """Load cached content for the specified version/data type."""

        cache_path = self.version_dir(version) / f"{data_type}.cache"
        if not cache_path.exists():
            return None

        with open(cache_path, "rb") as fh:
            return pickle.load(fh)

    def load_metadata(self, version: str, data_type: str) -> Optional[Dict[str, Any]]:
        metadata_path = self.version_dir(version) / f"{data_type}_meta.json"
        if not metadata_path.exists():
            return None
        try:
            with open(metadata_path, "r") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            return None

    def delete_version(self, version: str) -> None:
        version_dir = self.version_dir(version)
        if not version_dir.exists():
            return
        for path in version_dir.glob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                self._wipe_directory(path)
        version_dir.rmdir()

    def available_versions(self) -> Iterable[str]:
        if not self.root_dir.exists():
            return []
        return sorted(p.name for p in self.root_dir.iterdir() if p.is_dir())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def version_dir(self, version: str, *, create: bool = False) -> Path:
        version_key = version or "unknown"
        dir_path = self.root_dir / version_key
        if create:
            dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def _ensure_version_dir(self, version: str) -> Path:
        return self.version_dir(version, create=True)

    def _wipe_directory(self, path: Path) -> None:
        for child in path.glob("*"):
            if child.is_dir():
                self._wipe_directory(child)
                child.rmdir()
            else:
                child.unlink(missing_ok=True)


__all__ = ["CacheRepository"]


