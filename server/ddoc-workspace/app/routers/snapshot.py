"""
Snapshot management router
Integrates with ddoc SnapshotService
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List, Optional
import os
import json

from ..schemas import (
    SnapshotCreateRequest,
    SnapshotInfo,
    SnapshotRestoreRequest,
    LineageGraph,
    LineageNode,
    LineageEdge,
    SuccessResponse,
)

# Import ddoc services (installed via wheel)
from ddoc.core.snapshot_service import SnapshotService, get_snapshot_service

router = APIRouter()

WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))


def get_workspace_path(workspace_id: str) -> Path:
    """Get full path to workspace directory"""
    return WORKSPACES_ROOT / workspace_id


def get_snapshot_service_for_workspace(workspace_id: str) -> SnapshotService:
    """Get SnapshotService instance for a workspace"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    return get_snapshot_service(str(workspace_path))


def update_workspace_metadata_snapshot_count(workspace_id: str, count: int):
    """Update snapshot count in workspace metadata"""
    workspace_path = get_workspace_path(workspace_id)
    metadata_file = workspace_path / ".ddoc" / "workspace_meta.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        metadata["snapshot_count"] = count
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)


@router.post("/{workspace_id}/snapshot", response_model=SnapshotInfo)
async def create_snapshot(workspace_id: str, request: SnapshotCreateRequest):
    """
    Create a new snapshot of the current workspace state.
    
    - Commits data changes via DVC
    - Commits code changes via Git
    - Creates ddoc snapshot metadata
    """
    try:
        snapshot_service = get_snapshot_service_for_workspace(workspace_id)
        
        result = snapshot_service.create_snapshot(
            message=request.message,
            alias=request.alias,
            include_experiment=True,
            auto_commit=True,
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create snapshot: {result.get('error')}"
            )
        
        # Update metadata
        list_result = snapshot_service.list_snapshots()
        if list_result.get("success"):
            update_workspace_metadata_snapshot_count(workspace_id, list_result.get("count", 0))
        
        return SnapshotInfo(
            snapshot_id=result.get("snapshot_id", ""),
            alias=result.get("alias"),
            description=request.message,
            created_at=result.get("created_at", ""),
            git_commit=result.get("git_commit", ""),
            data_hash=result.get("data_hash", ""),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/snapshots", response_model=List[SnapshotInfo])
async def list_snapshots(workspace_id: str, limit: Optional[int] = None):
    """List all snapshots for a workspace"""
    try:
        snapshot_service = get_snapshot_service_for_workspace(workspace_id)
        
        result = snapshot_service.list_snapshots(limit=limit)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list snapshots: {result.get('error')}"
            )
        
        snapshots = []
        for snap in result.get("snapshots", []):
            snapshots.append(SnapshotInfo(
                snapshot_id=snap.get("snapshot_id", ""),
                alias=snap.get("alias"),
                description=snap.get("description", ""),
                created_at=snap.get("created_at", ""),
                git_commit=snap.get("git_commit", ""),
                data_hash=snap.get("data_hash", ""),
            ))
        
        return snapshots
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/snapshot/{snapshot_id}/restore", response_model=SuccessResponse)
async def restore_snapshot(
    workspace_id: str,
    snapshot_id: str,
    request: SnapshotRestoreRequest = SnapshotRestoreRequest()
):
    """
    Restore workspace to a specific snapshot.
    
    - Checkouts Git to the snapshot's commit
    - Checkouts DVC to restore data
    """
    try:
        snapshot_service = get_snapshot_service_for_workspace(workspace_id)
        
        result = snapshot_service.restore_snapshot(
            version_or_alias=snapshot_id,
            force=request.force,
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to restore snapshot: {result.get('error')}"
            )
        
        return SuccessResponse(
            success=True,
            message=f"Restored to snapshot {snapshot_id} (git: {result.get('git_commit')}, data: {result.get('data_hash')})"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/snapshot/{snapshot_id}", response_model=SnapshotInfo)
async def get_snapshot(workspace_id: str, snapshot_id: str):
    """Get details of a specific snapshot"""
    try:
        snapshot_service = get_snapshot_service_for_workspace(workspace_id)
        
        # Use list and filter since there's no direct get method
        result = snapshot_service.list_snapshots()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get snapshot: {result.get('error')}"
            )
        
        for snap in result.get("snapshots", []):
            if snap.get("snapshot_id") == snapshot_id or snap.get("alias") == snapshot_id:
                return SnapshotInfo(
                    snapshot_id=snap.get("snapshot_id", ""),
                    alias=snap.get("alias"),
                    description=snap.get("description", ""),
                    created_at=snap.get("created_at", ""),
                    git_commit=snap.get("git_commit", ""),
                    data_hash=snap.get("data_hash", ""),
                )
        
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{workspace_id}/snapshot/{snapshot_id}", response_model=SuccessResponse)
async def delete_snapshot(workspace_id: str, snapshot_id: str, force: bool = False):
    """Delete a specific snapshot"""
    try:
        snapshot_service = get_snapshot_service_for_workspace(workspace_id)
        
        result = snapshot_service.delete_snapshot(
            version_or_alias=snapshot_id,
            force=force,
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete snapshot: {result.get('error')}"
            )
        
        # Update metadata
        list_result = snapshot_service.list_snapshots()
        if list_result.get("success"):
            update_workspace_metadata_snapshot_count(workspace_id, list_result.get("count", 0))
        
        return SuccessResponse(
            success=True,
            message=f"Snapshot {snapshot_id} deleted"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/lineage", response_model=LineageGraph)
async def get_lineage_graph(workspace_id: str):
    """Get snapshot lineage graph for visualization"""
    try:
        snapshot_service = get_snapshot_service_for_workspace(workspace_id)
        
        result = snapshot_service.get_lineage_graph()
        
        if not result.get("success"):
            return LineageGraph(nodes=[], edges=[])
        
        nodes = []
        for node in result.get("nodes", []):
            nodes.append(LineageNode(
                id=node.get("id", ""),
                alias=node.get("alias"),
                description=node.get("description", ""),
                created_at=node.get("created_at", ""),
                git_commit=node.get("git_commit", ""),
                data_hash=node.get("data_hash", ""),
            ))
        
        edges = []
        for edge in result.get("edges", []):
            edges.append(LineageEdge(
                from_id=edge.get("from", ""),
                to_id=edge.get("to", ""),
                type=edge.get("type", "parent"),
            ))
        
        return LineageGraph(nodes=nodes, edges=edges)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/snapshot/current", response_model=Optional[SnapshotInfo])
async def get_current_snapshot(workspace_id: str):
    """Get the current snapshot (if workspace is at a snapshot state)"""
    try:
        snapshot_service = get_snapshot_service_for_workspace(workspace_id)
        
        current = snapshot_service.get_current_snapshot()
        
        if not current:
            return None
        
        return SnapshotInfo(
            snapshot_id=current.get("snapshot_id", ""),
            alias=current.get("alias"),
            description=current.get("description", ""),
            created_at=current.get("created_at", ""),
            git_commit=current.get("git_commit", ""),
            data_hash=current.get("data_hash", ""),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
