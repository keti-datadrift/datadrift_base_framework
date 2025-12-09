"""
Workspace management router
Integrates with ddoc WorkspaceService
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from typing import List, Optional
import os
import shutil
import json
from datetime import datetime

from ..schemas import (
    WorkspaceCreateRequest,
    WorkspaceInfo,
    WorkspaceStatus,
    WorkspaceType,
    SuccessResponse,
    ErrorResponse,
)

# Import ddoc services (installed via wheel)
from ddoc.core.workspace import WorkspaceService, get_workspace_service
from ddoc.core.snapshot_service import SnapshotService, get_snapshot_service

router = APIRouter()

WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))

# Container path mappings for cross-container compatibility
CONTAINER_PATH_MAPPINGS = {
    "/app/dvc_storage": "/dvc_storage",
    "/app/data": "/dvc_storage/datasets",  # Backend's /app/data maps to ddoc-workspace's /dvc_storage/datasets
    "/data": "/dvc_storage/datasets",      # Alternative path format
}


def convert_container_path(path_str: str) -> str:
    """Convert path between different container mount points"""
    for old_prefix, new_prefix in CONTAINER_PATH_MAPPINGS.items():
        if path_str.startswith(old_prefix):
            return path_str.replace(old_prefix, new_prefix, 1)
    return path_str


def get_workspace_path(workspace_id: str) -> Path:
    """Get full path to workspace directory"""
    return WORKSPACES_ROOT / workspace_id


def load_workspace_metadata(workspace_id: str) -> Optional[dict]:
    """Load workspace metadata from JSON file"""
    metadata_file = get_workspace_path(workspace_id) / ".ddoc" / "workspace_meta.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return None


def save_workspace_metadata(workspace_id: str, metadata: dict):
    """Save workspace metadata to JSON file"""
    workspace_path = get_workspace_path(workspace_id)
    metadata_file = workspace_path / ".ddoc" / "workspace_meta.json"
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


@router.post("/create", response_model=WorkspaceInfo)
async def create_workspace(request: WorkspaceCreateRequest):
    """
    Create a new workspace from a drift analysis dataset.
    
    - Initializes ddoc workspace structure
    - Copies/links source dataset
    - Creates initial snapshot
    """
    try:
        # Generate workspace ID
        workspace_id = f"{request.dataset_id}_{request.dataset_type.value}"
        workspace_path = get_workspace_path(workspace_id)
        
        # Check if workspace already exists
        if workspace_path.exists():
            # Load existing metadata
            metadata = load_workspace_metadata(workspace_id)
            if metadata:
                return WorkspaceInfo(
                    workspace_id=workspace_id,
                    name=metadata.get("name", workspace_id),
                    dataset_type=request.dataset_type,
                    source_dataset_id=request.dataset_id,
                    path=str(workspace_path),
                    created_at=metadata.get("created_at", ""),
                    has_git=metadata.get("has_git", False),
                    has_dvc=metadata.get("has_dvc", False),
                    has_ddoc=metadata.get("has_ddoc", False),
                    snapshot_count=metadata.get("snapshot_count", 0),
                    experiment_count=metadata.get("experiment_count", 0),
                )
        
        # Initialize workspace using ddoc WorkspaceService
        ws_service = get_workspace_service()
        result = ws_service.init_workspace(str(workspace_path), force=True)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize workspace: {result.get('error')}"
            )
        
        # Copy source dataset to workspace data directory
        # Convert path for cross-container compatibility
        converted_path = convert_container_path(request.source_path)
        source_path = Path(converted_path)
        data_copied = False
        
        print(f"[DEBUG] Original source path: {request.source_path}")
        print(f"[DEBUG] Converted source path: {converted_path}")
        print(f"[DEBUG] Source path exists: {source_path.exists()}")
        
        if source_path.exists():
            data_dir = workspace_path / "data" / source_path.name
            if not data_dir.exists():
                # Use symlink for large datasets, copy for small ones
                if source_path.is_dir():
                    shutil.copytree(source_path, data_dir)
                    data_copied = True
                    print(f"[DEBUG] Data copied to: {data_dir}")
                else:
                    shutil.copy2(source_path, data_dir)
                    data_copied = True
                    print(f"[DEBUG] File copied to: {data_dir}")
        else:
            print(f"[WARNING] Source path not found: {source_path}")
        
        # Save workspace metadata
        created_at = datetime.now().isoformat()
        initial_snapshot_count = 0
        
        # Create initial snapshot (baseline) if data was copied successfully
        if data_copied:
            try:
                snapshot_service = get_snapshot_service(str(workspace_path))
                snapshot_result = snapshot_service.create_snapshot(
                    message="초기 워크스페이스 상태 (baseline)",
                    alias="init",
                    include_experiment=False,
                    auto_commit=True,
                )
                if snapshot_result.get("success"):
                    initial_snapshot_count = 1
                    print(f"[DEBUG] Initial snapshot created: {snapshot_result.get('snapshot_id')}")
                else:
                    print(f"[WARNING] Failed to create initial snapshot: {snapshot_result.get('error')}")
            except Exception as e:
                print(f"[WARNING] Failed to create initial snapshot: {str(e)}")
        
        metadata = {
            "workspace_id": workspace_id,
            "name": request.name or workspace_id,
            "dataset_type": request.dataset_type.value,
            "source_dataset_id": request.dataset_id,
            "source_path": request.source_path,
            "created_at": created_at,
            "has_git": result.get("git_initialized", False),
            "has_dvc": result.get("dvc_initialized", False),
            "has_ddoc": True,
            "snapshot_count": initial_snapshot_count,
            "experiment_count": 0,
        }
        save_workspace_metadata(workspace_id, metadata)
        
        return WorkspaceInfo(
            workspace_id=workspace_id,
            name=metadata["name"],
            dataset_type=request.dataset_type,
            source_dataset_id=request.dataset_id,
            path=str(workspace_path),
            created_at=created_at,
            has_git=metadata["has_git"],
            has_dvc=metadata["has_dvc"],
            has_ddoc=metadata["has_ddoc"],
            snapshot_count=initial_snapshot_count,
            experiment_count=0,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/status", response_model=WorkspaceStatus)
async def get_workspace_status(workspace_id: str):
    """Get workspace status and verification"""
    workspace_path = get_workspace_path(workspace_id)
    
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    try:
        ws_service = get_workspace_service(str(workspace_path))
        verify_result = ws_service.verify_workspace(str(workspace_path))
        
        # Get current snapshot if any
        current_snapshot = None
        snapshot_service = SnapshotService(str(workspace_path))
        current = snapshot_service.get_current_snapshot()
        if current:
            current_snapshot = current.get("snapshot_id")
        
        return WorkspaceStatus(
            workspace_id=workspace_id,
            is_valid=verify_result.get("is_valid", False),
            has_git=verify_result.get("has_git", False),
            has_dvc=verify_result.get("has_dvc", False),
            has_ddoc=verify_result.get("has_ddoc", False),
            current_snapshot=current_snapshot,
            uncommitted_changes=False,  # TODO: Check git status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("s", response_model=List[WorkspaceInfo])
async def list_workspaces():
    """List all workspaces"""
    workspaces = []
    
    if not WORKSPACES_ROOT.exists():
        return workspaces
    
    for workspace_dir in WORKSPACES_ROOT.iterdir():
        if workspace_dir.is_dir() and not workspace_dir.name.startswith('.'):
            metadata = load_workspace_metadata(workspace_dir.name)
            if metadata:
                workspaces.append(WorkspaceInfo(
                    workspace_id=workspace_dir.name,
                    name=metadata.get("name", workspace_dir.name),
                    dataset_type=WorkspaceType(metadata.get("dataset_type", "base")),
                    source_dataset_id=metadata.get("source_dataset_id", ""),
                    path=str(workspace_dir),
                    created_at=metadata.get("created_at", ""),
                    has_git=metadata.get("has_git", False),
                    has_dvc=metadata.get("has_dvc", False),
                    has_ddoc=metadata.get("has_ddoc", False),
                    snapshot_count=metadata.get("snapshot_count", 0),
                    experiment_count=metadata.get("experiment_count", 0),
                ))
    
    return workspaces


@router.delete("/{workspace_id}", response_model=SuccessResponse)
async def delete_workspace(workspace_id: str, force: bool = False):
    """Delete a workspace"""
    workspace_path = get_workspace_path(workspace_id)
    
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    try:
        # Check for uncommitted changes unless force
        if not force:
            metadata = load_workspace_metadata(workspace_id)
            if metadata and metadata.get("snapshot_count", 0) > 0:
                # Check if there are uncommitted changes
                pass  # TODO: Implement check
        
        # Remove workspace directory
        shutil.rmtree(workspace_path)
        
        return SuccessResponse(
            success=True,
            message=f"Workspace {workspace_id} deleted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/info", response_model=WorkspaceInfo)
async def get_workspace_info(workspace_id: str):
    """Get detailed workspace information"""
    workspace_path = get_workspace_path(workspace_id)
    
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    metadata = load_workspace_metadata(workspace_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Workspace metadata not found")
    
    # Count snapshots
    snapshots_dir = workspace_path / ".ddoc" / "snapshots"
    snapshot_count = len(list(snapshots_dir.glob("v*.yaml"))) if snapshots_dir.exists() else 0
    
    # Count experiments
    experiments_dir = workspace_path / "experiments"
    experiment_count = len([d for d in experiments_dir.iterdir() if d.is_dir()]) if experiments_dir.exists() else 0
    
    return WorkspaceInfo(
        workspace_id=workspace_id,
        name=metadata.get("name", workspace_id),
        dataset_type=WorkspaceType(metadata.get("dataset_type", "base")),
        source_dataset_id=metadata.get("source_dataset_id", ""),
        path=str(workspace_path),
        created_at=metadata.get("created_at", ""),
        has_git=metadata.get("has_git", False),
        has_dvc=metadata.get("has_dvc", False),
        has_ddoc=metadata.get("has_ddoc", False),
        snapshot_count=snapshot_count,
        experiment_count=experiment_count,
    )
