"""
Data operations router
Handles data transformation based on FiftyOne views and automatic snapshot creation
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Optional, List
import os
import shutil
import json
from datetime import datetime

from pydantic import BaseModel

# Import ddoc services
from ddoc.core.snapshot_service import get_snapshot_service

router = APIRouter()

WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))


class ApplyViewRequest(BaseModel):
    """Request to apply a FiftyOne view transformation"""
    view_name: str
    operation: str = "keep_only"  # "keep_only" | "remove"
    snapshot_message: str
    snapshot_alias: Optional[str] = None
    dry_run: bool = False


class TransformationResult(BaseModel):
    """Result of a data transformation"""
    success: bool
    files_removed: int
    files_kept: int
    snapshot_id: Optional[str] = None
    message: str


class PreviewResult(BaseModel):
    """Preview of transformation without applying"""
    operation: str
    files_to_remove: int
    files_to_keep: int
    sample_files_to_remove: List[str]
    message: str


def get_workspace_path(workspace_id: str) -> Path:
    """Get full path to workspace directory"""
    return WORKSPACES_ROOT / workspace_id


def get_workspace_data_path(workspace_id: str) -> Path:
    """Get path to workspace data directory"""
    workspace_path = get_workspace_path(workspace_id)
    data_path = workspace_path / "data"
    
    # Find first dataset directory
    if data_path.exists():
        for item in data_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                return item
    return data_path


def load_view_sample_ids(workspace_id: str, view_name: str) -> set:
    """
    Load sample IDs from a saved FiftyOne view
    
    Note: In a full implementation, this would connect to FiftyOne
    and retrieve the actual sample IDs from the view. For now, we
    load from a cached view definition file.
    """
    workspace_path = get_workspace_path(workspace_id)
    views_file = workspace_path / ".ddoc" / "fiftyone_views.json"
    
    if not views_file.exists():
        return set()
    
    with open(views_file, 'r') as f:
        views_data = json.load(f)
    
    for view in views_data.get("views", []):
        if view["name"] == view_name:
            # In full implementation, this would be actual sample IDs
            # For now, return sample_ids if cached
            return set(view.get("sample_ids", []))
    
    return set()


def get_all_data_files(data_path: Path) -> dict:
    """
    Get all data files (images and labels) from dataset path
    Returns: {filename_without_ext: {"image": path, "label": path}}
    """
    files = {}
    
    # Common image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    
    # Check for YOLO-style structure
    images_dir = data_path / "images"
    labels_dir = data_path / "labels"
    
    if images_dir.exists():
        # YOLO structure
        for split in ["train", "val", "valid", "test"]:
            split_images = images_dir / split
            split_labels = labels_dir / split
            
            if split_images.exists():
                for img_path in split_images.iterdir():
                    if img_path.suffix.lower() in image_extensions:
                        stem = img_path.stem
                        files[f"{split}/{stem}"] = {
                            "image": img_path,
                            "label": split_labels / f"{stem}.txt" if split_labels.exists() else None
                        }
        
        # Also check root images folder
        for img_path in images_dir.iterdir():
            if img_path.is_file() and img_path.suffix.lower() in image_extensions:
                stem = img_path.stem
                files[stem] = {
                    "image": img_path,
                    "label": labels_dir / f"{stem}.txt" if labels_dir.exists() else None
                }
    else:
        # Flat structure or other format
        for img_path in data_path.rglob("*"):
            if img_path.is_file() and img_path.suffix.lower() in image_extensions:
                rel_path = img_path.relative_to(data_path)
                stem = rel_path.stem
                parent = str(rel_path.parent) if rel_path.parent != Path(".") else ""
                key = f"{parent}/{stem}" if parent else stem
                files[key] = {"image": img_path, "label": None}
    
    return files


@router.post("/{workspace_id}/data/apply-view", response_model=TransformationResult)
async def apply_view_changes(workspace_id: str, request: ApplyViewRequest):
    """
    Apply FiftyOne view-based data transformation and create snapshot
    
    This endpoint:
    1. Loads the saved FiftyOne view
    2. Identifies files to keep/remove based on operation
    3. Deletes files (if not dry_run)
    4. Creates a mandatory snapshot with the changes
    
    Operations:
    - keep_only: Keep only files in the view, remove everything else
    - remove: Remove files in the view, keep everything else
    """
    workspace_path = get_workspace_path(workspace_id)
    
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    data_path = get_workspace_data_path(workspace_id)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="No data found in workspace")
    
    # Get all files
    all_files = get_all_data_files(data_path)
    total_files = len(all_files)
    
    if total_files == 0:
        raise HTTPException(status_code=400, detail="No data files found")
    
    # Load view sample IDs (in full implementation, this would query FiftyOne)
    view_sample_ids = load_view_sample_ids(workspace_id, request.view_name)
    
    # For now, if no sample IDs are cached, we'll use the view_name as a pattern
    # In production, this should integrate with FiftyOne properly
    if not view_sample_ids:
        # Fallback: treat view_name as a tag/filter pattern
        # This is a placeholder - real implementation would query FiftyOne
        return TransformationResult(
            success=False,
            files_removed=0,
            files_kept=total_files,
            message=f"View '{request.view_name}' not found or has no cached sample IDs. Please save the view in FiftyOne first."
        )
    
    # Determine files to keep/remove
    if request.operation == "keep_only":
        files_to_remove = {k: v for k, v in all_files.items() if k not in view_sample_ids}
        files_to_keep = {k: v for k, v in all_files.items() if k in view_sample_ids}
    elif request.operation == "remove":
        files_to_remove = {k: v for k, v in all_files.items() if k in view_sample_ids}
        files_to_keep = {k: v for k, v in all_files.items() if k not in view_sample_ids}
    else:
        raise HTTPException(status_code=400, detail=f"Invalid operation: {request.operation}")
    
    # Dry run - just return preview
    if request.dry_run:
        return TransformationResult(
            success=True,
            files_removed=len(files_to_remove),
            files_kept=len(files_to_keep),
            message=f"미리보기: {len(files_to_remove)}개 파일 삭제 예정, {len(files_to_keep)}개 유지"
        )
    
    # Apply transformation
    removed_count = 0
    for file_id, file_paths in files_to_remove.items():
        try:
            # Remove image
            if file_paths["image"] and file_paths["image"].exists():
                file_paths["image"].unlink()
                removed_count += 1
            
            # Remove label if exists
            if file_paths.get("label") and file_paths["label"].exists():
                file_paths["label"].unlink()
        except Exception as e:
            print(f"[WARNING] Failed to remove {file_id}: {e}")
    
    # Create mandatory snapshot
    if removed_count > 0:
        try:
            snapshot_service = get_snapshot_service(str(workspace_path))
            snapshot_result = snapshot_service.create_snapshot(
                message=request.snapshot_message,
                alias=request.snapshot_alias,
                include_experiment=False,
                auto_commit=True,
            )
            
            snapshot_id = snapshot_result.get("snapshot_id") if snapshot_result.get("success") else None
        except Exception as e:
            print(f"[WARNING] Failed to create snapshot: {e}")
            snapshot_id = None
    else:
        snapshot_id = None
    
    return TransformationResult(
        success=True,
        files_removed=removed_count,
        files_kept=len(files_to_keep),
        snapshot_id=snapshot_id,
        message=f"{removed_count}개 파일 삭제, {len(files_to_keep)}개 유지" + 
                (f", 스냅샷 {snapshot_id} 생성됨" if snapshot_id else "")
    )


@router.post("/{workspace_id}/data/preview-transform", response_model=PreviewResult)
async def preview_transformation(workspace_id: str, request: ApplyViewRequest):
    """
    Preview a transformation without applying it
    """
    workspace_path = get_workspace_path(workspace_id)
    
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    data_path = get_workspace_data_path(workspace_id)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="No data found in workspace")
    
    # Get all files
    all_files = get_all_data_files(data_path)
    total_files = len(all_files)
    
    # Load view
    view_sample_ids = load_view_sample_ids(workspace_id, request.view_name)
    
    if not view_sample_ids:
        # Return preview based on total files
        return PreviewResult(
            operation=request.operation,
            files_to_remove=0,
            files_to_keep=total_files,
            sample_files_to_remove=[],
            message=f"View '{request.view_name}' not found. Total files: {total_files}"
        )
    
    # Determine files to remove
    if request.operation == "keep_only":
        files_to_remove = [k for k in all_files.keys() if k not in view_sample_ids]
    else:
        files_to_remove = [k for k in all_files.keys() if k in view_sample_ids]
    
    files_to_keep = total_files - len(files_to_remove)
    
    return PreviewResult(
        operation=request.operation,
        files_to_remove=len(files_to_remove),
        files_to_keep=files_to_keep,
        sample_files_to_remove=files_to_remove[:10],  # Show first 10
        message=f"작업: {request.operation}, 삭제 예정: {len(files_to_remove)}개, 유지: {files_to_keep}개"
    )


@router.delete("/{workspace_id}/data/files")
async def delete_specific_files(
    workspace_id: str,
    file_ids: List[str],
    snapshot_message: str,
    snapshot_alias: Optional[str] = None
):
    """
    Delete specific files by their IDs and create a snapshot
    
    This is an alternative to view-based deletion for direct file removal.
    """
    workspace_path = get_workspace_path(workspace_id)
    
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    data_path = get_workspace_data_path(workspace_id)
    all_files = get_all_data_files(data_path)
    
    removed_count = 0
    for file_id in file_ids:
        if file_id in all_files:
            file_paths = all_files[file_id]
            try:
                if file_paths["image"] and file_paths["image"].exists():
                    file_paths["image"].unlink()
                    removed_count += 1
                if file_paths.get("label") and file_paths["label"].exists():
                    file_paths["label"].unlink()
            except Exception as e:
                print(f"[WARNING] Failed to remove {file_id}: {e}")
    
    # Create mandatory snapshot
    snapshot_id = None
    if removed_count > 0:
        try:
            snapshot_service = get_snapshot_service(str(workspace_path))
            snapshot_result = snapshot_service.create_snapshot(
                message=snapshot_message,
                alias=snapshot_alias,
                auto_commit=True,
            )
            snapshot_id = snapshot_result.get("snapshot_id") if snapshot_result.get("success") else None
        except Exception as e:
            print(f"[WARNING] Failed to create snapshot: {e}")
    
    return {
        "success": True,
        "files_removed": removed_count,
        "snapshot_id": snapshot_id,
        "message": f"{removed_count}개 파일 삭제됨" + (f", 스냅샷 {snapshot_id}" if snapshot_id else "")
    }

