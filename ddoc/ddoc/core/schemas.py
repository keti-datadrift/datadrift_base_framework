"""
Pydantic schemas for ddoc snapshot and configuration
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class DataSnapshot(BaseModel):
    """Data component of a snapshot"""
    dvc_hash: str = Field(..., description="DVC hash of data/ directory")
    path: str = Field(default="data/", description="Path to data directory")
    contents: List[str] = Field(default_factory=list, description="List of datasets in data/")
    stats: Optional[Dict[str, Any]] = Field(default=None, description="Data statistics")


class CodeSnapshot(BaseModel):
    """Code component of a snapshot"""
    git_rev: str = Field(..., description="Git commit hash")
    branch: Optional[str] = Field(default=None, description="Git branch name")
    files: List[str] = Field(default_factory=list, description="Main code files")


class ExperimentSnapshot(BaseModel):
    """Experiment component of a snapshot"""
    id: str = Field(..., description="Experiment ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="Experiment parameters")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Experiment metrics")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="Artifact paths")


class LineageSnapshot(BaseModel):
    """Lineage information for a snapshot"""
    parent_snapshot: Optional[str] = Field(default=None, description="Parent snapshot ID")
    experiments_run: List[str] = Field(default_factory=list, description="Experiments run in this snapshot")


class Snapshot(BaseModel):
    """Complete snapshot schema"""
    snapshot_id: str = Field(..., description="Unique snapshot identifier (e.g., v01, v02)")
    alias: Optional[str] = Field(default=None, description="Human-readable alias")
    created_at: str = Field(..., description="ISO format timestamp")
    description: str = Field(..., description="Snapshot description/message")
    
    data: DataSnapshot = Field(..., description="Data state")
    code: CodeSnapshot = Field(..., description="Code state")
    experiment: Optional[ExperimentSnapshot] = Field(default=None, description="Experiment results")
    lineage: Optional[LineageSnapshot] = Field(default=None, description="Lineage information")
    
    # Round-9 — migrated from class-based ``class Config`` to
    # ``model_config`` per Pydantic V2 (the legacy form raises a
    # PydanticDeprecatedSince20 warning under pydantic >= 2.0).
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "snapshot_id": "v01",
                "alias": "baseline",
                "created_at": "2025-11-14T10:00:00",
                "description": "baseline model with cleaned data",
                "data": {
                    "dvc_hash": "3f12ab9.dir",
                    "path": "data/",
                    "contents": ["test_data", "yolo_reference"],
                    "stats": {
                        "total_files": 1000,
                        "total_size_mb": 500,
                    },
                },
                "code": {
                    "git_rev": "af31bdc",
                    "branch": "main",
                    "files": ["code/train.py", "code/model.py"],
                },
                "experiment": {
                    "id": "exp_001",
                    "params": {"lr": 0.001, "batch": 64},
                    "metrics": {"accuracy": 0.912},
                    "artifacts": {"checkpoint": "experiments/exp_001/best.pt"},
                },
                "lineage": {
                    "parent_snapshot": None,
                    "experiments_run": ["exp_001"],
                },
            }
        }
    )


class AliasMapping(BaseModel):
    """Mapping of aliases to snapshot versions"""
    mappings: Dict[str, str] = Field(default_factory=dict, description="Alias -> version mapping")
    
    def get_version(self, alias: str) -> Optional[str]:
        """Get version for an alias"""
        return self.mappings.get(alias)
    
    def set_alias(self, alias: str, version: str) -> None:
        """Set an alias for a version"""
        self.mappings[alias] = version
    
    def remove_alias(self, alias: str) -> bool:
        """Remove an alias"""
        if alias in self.mappings:
            del self.mappings[alias]
            return True
        return False
    
    def get_alias(self, version: str) -> Optional[str]:
        """Get alias for a version (reverse lookup)"""
        for alias, ver in self.mappings.items():
            if ver == version:
                return alias
        return None


class WorkspaceConfig(BaseModel):
    """Workspace configuration schema"""
    version: str = Field(default="2.0", description="ddoc version")
    project: Dict[str, Any] = Field(default_factory=dict, description="Project metadata")
    snapshot: Dict[str, Any] = Field(default_factory=dict, description="Snapshot settings")
    tracking: Dict[str, Any] = Field(default_factory=dict, description="Tracking settings")


class FileMetadata(BaseModel):
    """File metadata for incremental analysis"""
    file_path: str = Field(..., description="File path relative to data directory")
    file_hash: str = Field(..., description="File content hash")
    file_size: int = Field(..., description="File size in bytes")
    file_mtime: float = Field(..., description="File modification time")
    analyzed_at: str = Field(..., description="Analysis timestamp")


class AnalysisCache(BaseModel):
    """Analysis cache schema with incremental analysis support"""
    data_hash: str = Field(..., description="Data hash this cache belongs to")
    created_at: str = Field(..., description="Cache creation timestamp")
    last_accessed: Optional[str] = Field(default=None, description="Last access timestamp")
    
    # Analysis results
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Statistical summaries")
    distributions: Dict[str, Any] = Field(default_factory=dict, description="Distribution information")
    embedding_summary: Optional[Dict[str, Any]] = Field(default=None, description="Embedding summary stats")
    cluster_info: Optional[Dict[str, Any]] = Field(default=None, description="Cluster information")
    
    # Incremental analysis metadata
    file_metadata: Dict[str, FileMetadata] = Field(default_factory=dict, description="File-level metadata")
    incremental_info: Optional[Dict[str, Any]] = Field(default=None, description="Incremental analysis information")


class CacheSummary(BaseModel):
    """Cache summary for drift analysis (legacy compatibility)"""
    snapshot_id: str = Field(..., description="Snapshot ID this cache belongs to")
    created_at: str = Field(..., description="Cache creation timestamp")
    data_hash: str = Field(..., description="Data hash this cache was created from")
    
    # Statistical summaries
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Statistical summaries")
    distributions: Dict[str, Any] = Field(default_factory=dict, description="Distribution information")
    
    # Optional embeddings
    embedding_summary: Optional[Dict[str, Any]] = Field(default=None, description="Embedding summary stats")
    cluster_info: Optional[Dict[str, Any]] = Field(default=None, description="Cluster information")

