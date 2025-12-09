"""
Pydantic schemas for ddoc-workspace API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ===========================================
# Enums
# ===========================================

class WorkspaceType(str, Enum):
    BASE = "base"
    TARGET = "target"


class DatasetFormat(str, Enum):
    YOLO = "yolo"
    COCO = "coco"
    VOC = "voc"
    UNKNOWN = "unknown"


class SamplingStrategy(str, Enum):
    RANDOM = "random"
    STRATIFIED = "stratified"
    THRESHOLD = "threshold"


class ExportFormat(str, Enum):
    YOLO = "yolo"
    COCO = "coco"
    VOC = "voc"


# ===========================================
# Workspace Schemas
# ===========================================

class WorkspaceCreateRequest(BaseModel):
    """Request to create a new workspace"""
    dataset_id: str = Field(..., description="Source dataset ID from drift analysis")
    dataset_type: WorkspaceType = Field(..., description="base or target")
    source_path: str = Field(..., description="Path to source dataset")
    name: Optional[str] = Field(None, description="Optional workspace name")


class WorkspaceInfo(BaseModel):
    """Workspace information response"""
    workspace_id: str
    name: str
    dataset_type: WorkspaceType
    source_dataset_id: str
    path: str
    created_at: str
    has_git: bool
    has_dvc: bool
    has_ddoc: bool
    snapshot_count: int = 0
    experiment_count: int = 0


class WorkspaceStatus(BaseModel):
    """Workspace status response"""
    workspace_id: str
    is_valid: bool
    has_git: bool
    has_dvc: bool
    has_ddoc: bool
    current_snapshot: Optional[str] = None
    uncommitted_changes: bool = False


# ===========================================
# Snapshot Schemas
# ===========================================

class SnapshotCreateRequest(BaseModel):
    """Request to create a snapshot"""
    message: str = Field(..., description="Snapshot description")
    alias: Optional[str] = Field(None, description="Optional alias for the snapshot")


class SnapshotInfo(BaseModel):
    """Snapshot information"""
    snapshot_id: str
    alias: Optional[str]
    description: str
    created_at: str
    git_commit: str
    data_hash: str


class SnapshotRestoreRequest(BaseModel):
    """Request to restore a snapshot"""
    force: bool = Field(False, description="Force restore even with uncommitted changes")


class LineageNode(BaseModel):
    """Node in lineage graph"""
    id: str
    alias: Optional[str]
    description: str
    created_at: str
    git_commit: str
    data_hash: str


class LineageEdge(BaseModel):
    """Edge in lineage graph"""
    from_id: str
    to_id: str
    type: str = "parent"


class LineageGraph(BaseModel):
    """Lineage graph response"""
    nodes: List[LineageNode]
    edges: List[LineageEdge]


# ===========================================
# Analysis Schemas
# ===========================================

class AnalysisRequest(BaseModel):
    """Request for analysis"""
    force_recompute: bool = Field(False, description="Force recomputation even if cached")


class EmbeddingAnalysisParams(BaseModel):
    """Parameters for embedding analysis"""
    model: str = Field("dinov2", description="Embedding model (dinov2, clip, resnet)")
    batch_size: int = Field(32, description="Batch size for processing")


class AttributeAnalysisParams(BaseModel):
    """Parameters for attribute analysis"""
    compute_noise: bool = Field(True)
    compute_sharpness: bool = Field(True)
    compute_brightness: bool = Field(True)


class AnalysisResult(BaseModel):
    """Analysis result response"""
    workspace_id: str
    analysis_type: str
    status: str
    cached: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ===========================================
# Sampling Schemas
# ===========================================

class DataItem(BaseModel):
    """Single data item"""
    id: str
    filename: str
    path: str
    split: Optional[str] = None
    label: Optional[str] = None
    thumbnail_url: Optional[str] = None
    size_bytes: int = 0
    width: Optional[int] = None
    height: Optional[int] = None


class DataItemsResponse(BaseModel):
    """Paginated data items response"""
    items: List[DataItem]
    total: int
    offset: int
    limit: int
    splits: List[str]
    classes: List[str]


class DatasetStats(BaseModel):
    """Dataset statistics"""
    total_items: int
    total_size_mb: float
    format: DatasetFormat
    splits: Dict[str, int]
    classes: Dict[str, int]
    image_stats: Optional[Dict[str, Any]] = None


class AddItemsRequest(BaseModel):
    """Request to add items"""
    source_paths: List[str] = Field(..., description="Paths to items to add")
    target_split: str = Field("train", description="Target split")


class RemoveItemsRequest(BaseModel):
    """Request to remove items"""
    item_ids: List[str] = Field(..., description="IDs of items to remove")


class MoveItemsRequest(BaseModel):
    """Request to move items between splits"""
    item_ids: List[str] = Field(..., description="IDs of items to move")
    target_split: str = Field(..., description="Target split")


class RelabelItemsRequest(BaseModel):
    """Request to relabel items"""
    item_ids: List[str] = Field(..., description="IDs of items to relabel")
    new_label: str = Field(..., description="New label")


class SampleRequest(BaseModel):
    """Request to create a sample dataset"""
    strategy: SamplingStrategy = Field(..., description="Sampling strategy")
    params: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    output_name: str = Field(..., description="Name for sampled dataset")


class SampleResult(BaseModel):
    """Sample creation result"""
    success: bool
    sample_path: str
    item_count: int
    strategy: str
    params: Dict[str, Any]


class ExportRequest(BaseModel):
    """Request to export dataset"""
    format: ExportFormat = Field(..., description="Export format")
    output_path: Optional[str] = Field(None, description="Custom output path")
    include_splits: Optional[List[str]] = Field(None, description="Splits to include")


class ExportResult(BaseModel):
    """Export result"""
    success: bool
    format: str
    output_path: str
    item_count: int
    size_mb: float


# ===========================================
# Experiment Schemas
# ===========================================

class CodeUploadResponse(BaseModel):
    """Response after code upload"""
    success: bool
    filename: str
    path: str


class CodeTemplate(BaseModel):
    """Code template info"""
    name: str
    description: str
    filename: str
    content: str


class ExperimentRunRequest(BaseModel):
    """Request to run an experiment"""
    name: str = Field(..., description="Experiment name")
    trainer_script: str = Field(..., description="Path to trainer script")
    params: Dict[str, Any] = Field(default_factory=dict, description="Training parameters")
    dataset_version: Optional[str] = Field(None, description="Dataset version to use")


class ExperimentInfo(BaseModel):
    """Experiment information"""
    experiment_id: str
    mlflow_run_id: Optional[str]
    name: str
    status: str
    dataset_version: str
    params: Dict[str, Any]
    metrics: Dict[str, Any]
    created_at: str
    completed_at: Optional[str] = None


class ExperimentListResponse(BaseModel):
    """List of experiments"""
    experiments: List[ExperimentInfo]
    total: int


# ===========================================
# Common Response Schemas
# ===========================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None
