"""
Sampling router
Provides data exploration, modification, sampling, and export endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from typing import Optional, List
import os
import base64
import io

from ..schemas import (
    DataItem,
    DataItemsResponse,
    DatasetStats,
    DatasetFormat,
    AddItemsRequest,
    RemoveItemsRequest,
    MoveItemsRequest,
    RelabelItemsRequest,
    SampleRequest,
    SampleResult,
    SamplingStrategy,
    ExportRequest,
    ExportResult,
    ExportFormat,
    SuccessResponse,
)
from ..services.sampling_service import (
    SamplingService,
    SamplingStrategy as SamplingStrategyEnum,
)

router = APIRouter()

WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))


def get_workspace_path(workspace_id: str) -> Path:
    """Get full path to workspace directory"""
    return WORKSPACES_ROOT / workspace_id


def get_sampling_service(workspace_id: str) -> SamplingService:
    """Get SamplingService instance for a workspace"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    return SamplingService(str(workspace_path))


# ===========================================
# Data Exploration
# ===========================================

@router.get("/{workspace_id}/data/items", response_model=DataItemsResponse)
async def list_items(
    workspace_id: str,
    split: Optional[str] = Query(None, description="Filter by split (train, valid, test)"),
    class_filter: Optional[str] = Query(None, description="Filter by class name/index"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List data items with optional filtering and pagination.
    
    Returns images with metadata and optional label information.
    """
    try:
        service = get_sampling_service(workspace_id)
        items, total = service.list_items(
            split=split,
            class_filter=class_filter,
            limit=limit,
            offset=offset,
        )
        
        # Convert to response model
        response_items = [
            DataItem(
                id=item.id,
                filename=item.filename,
                path=item.path,
                split=item.split,
                label=item.label,
                thumbnail_url=f"/workspace/{workspace_id}/data/item/{item.id}/thumbnail",
                size_bytes=item.size_bytes,
                width=item.width,
                height=item.height,
            )
            for item in items
        ]
        
        # Get splits and classes
        stats = service.get_statistics()
        
        return DataItemsResponse(
            items=response_items,
            total=total,
            offset=offset,
            limit=limit,
            splits=list(stats.splits.keys()),
            classes=list(stats.classes.keys()),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/data/item/{item_id}/preview")
async def get_item_preview(workspace_id: str, item_id: str):
    """
    Get detailed preview of a specific item.
    
    Returns full metadata and label content.
    """
    try:
        service = get_sampling_service(workspace_id)
        preview = service.get_item_preview(item_id)
        
        if not preview:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        
        return preview
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/data/item/{item_id}/thumbnail")
async def get_item_thumbnail(workspace_id: str, item_id: str, size: int = 200):
    """
    Get thumbnail image for an item.
    
    Returns resized image for grid display.
    """
    try:
        service = get_sampling_service(workspace_id)
        preview = service.get_item_preview(item_id)
        
        if not preview:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        
        image_path = Path(preview["path"])
        
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found")
        
        try:
            from PIL import Image
            
            # Open and resize image
            img = Image.open(image_path)
            img.thumbnail((size, size))
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            buffer.seek(0)
            
            return StreamingResponse(buffer, media_type="image/jpeg")
            
        except ImportError:
            # If PIL not available, return original file
            return FileResponse(image_path)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/data/item/{item_id}/image")
async def get_item_image(workspace_id: str, item_id: str):
    """
    Get full-size image for an item.
    """
    try:
        service = get_sampling_service(workspace_id)
        preview = service.get_item_preview(item_id)
        
        if not preview:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        
        image_path = Path(preview["path"])
        
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found")
        
        return FileResponse(image_path)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/data/stats")
async def get_dataset_stats(workspace_id: str):
    """
    Get dataset statistics.
    
    Returns counts by split, class distribution, and size information.
    """
    try:
        service = get_sampling_service(workspace_id)
        stats = service.get_statistics()
        
        return DatasetStats(
            total_items=stats.total_items,
            total_size_mb=stats.total_size_mb,
            format=DatasetFormat(stats.format.value),
            splits=stats.splits,
            classes=stats.classes,
            image_stats=stats.image_stats,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Data Modification
# ===========================================

@router.post("/{workspace_id}/data/add", response_model=SuccessResponse)
async def add_items(workspace_id: str, request: AddItemsRequest):
    """
    Add items to the dataset.
    
    Copies files from source paths to the dataset.
    """
    try:
        service = get_sampling_service(workspace_id)
        result = service.add_items(
            source_paths=request.source_paths,
            target_split=request.target_split,
        )
        
        if result.get("errors"):
            return SuccessResponse(
                success=True,
                message=f"Added {result['added']} items with {len(result['errors'])} errors: {result['errors'][:3]}"
            )
        
        return SuccessResponse(
            success=True,
            message=f"Added {result['added']} items to {request.target_split}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/data/remove", response_model=SuccessResponse)
async def remove_items(workspace_id: str, request: RemoveItemsRequest):
    """
    Remove items from the dataset.
    
    Deletes image and label files.
    """
    try:
        service = get_sampling_service(workspace_id)
        result = service.remove_items(item_ids=request.item_ids)
        
        if result.get("errors"):
            return SuccessResponse(
                success=True,
                message=f"Removed {result['removed']} items with {len(result['errors'])} errors"
            )
        
        return SuccessResponse(
            success=True,
            message=f"Removed {result['removed']} items"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/data/move", response_model=SuccessResponse)
async def move_items(workspace_id: str, request: MoveItemsRequest):
    """
    Move items between splits.
    
    Moves image and label files to new split directory.
    """
    try:
        service = get_sampling_service(workspace_id)
        result = service.move_items(
            item_ids=request.item_ids,
            target_split=request.target_split,
        )
        
        if result.get("errors"):
            return SuccessResponse(
                success=True,
                message=f"Moved {result['moved']} items with {len(result['errors'])} errors"
            )
        
        return SuccessResponse(
            success=True,
            message=f"Moved {result['moved']} items to {request.target_split}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/data/relabel", response_model=SuccessResponse)
async def relabel_items(workspace_id: str, request: RelabelItemsRequest):
    """
    Relabel items (change class).
    
    Updates label files with new class index.
    """
    try:
        service = get_sampling_service(workspace_id)
        result = service.relabel_items(
            item_ids=request.item_ids,
            new_label=request.new_label,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        if result.get("errors"):
            return SuccessResponse(
                success=True,
                message=f"Relabeled {result['relabeled']} items with {len(result['errors'])} errors"
            )
        
        return SuccessResponse(
            success=True,
            message=f"Relabeled {result['relabeled']} items to {request.new_label}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Sampling
# ===========================================

@router.post("/{workspace_id}/data/sample", response_model=SampleResult)
async def create_sample(workspace_id: str, request: SampleRequest):
    """
    Create a sampled dataset using specified strategy.
    
    Strategies:
    - random: Random sampling of n items
    - stratified: Maintains class distribution
    - threshold: Filter by criteria (e.g., size, drift score)
    """
    try:
        service = get_sampling_service(workspace_id)
        
        # Convert strategy enum
        strategy_map = {
            SamplingStrategy.RANDOM: SamplingStrategyEnum.RANDOM,
            SamplingStrategy.STRATIFIED: SamplingStrategyEnum.STRATIFIED,
            SamplingStrategy.THRESHOLD: SamplingStrategyEnum.THRESHOLD,
        }
        
        result = service.create_sample(
            strategy=strategy_map[request.strategy],
            params=request.params,
            output_name=request.output_name,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        return SampleResult(
            success=True,
            sample_path=result["sample_path"],
            item_count=result["item_count"],
            strategy=result["strategy"],
            params=result["params"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/data/samples")
async def list_samples(workspace_id: str):
    """List all sampled datasets"""
    try:
        workspace_path = get_workspace_path(workspace_id)
        samples_dir = workspace_path / "samples"
        
        if not samples_dir.exists():
            return {"samples": []}
        
        samples = []
        for sample_dir in samples_dir.iterdir():
            if sample_dir.is_dir():
                # Count items in sample
                item_count = len(list(sample_dir.rglob("*.jpg"))) + len(list(sample_dir.rglob("*.png")))
                
                samples.append({
                    "name": sample_dir.name,
                    "path": str(sample_dir),
                    "item_count": item_count,
                })
        
        return {"samples": samples}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Export
# ===========================================

@router.post("/{workspace_id}/data/export", response_model=ExportResult)
async def export_dataset(workspace_id: str, request: ExportRequest):
    """
    Export dataset to specified format.
    
    Supported formats:
    - yolo: YOLO format (images/ + labels/)
    - coco: COCO JSON format
    - voc: Pascal VOC XML format
    """
    try:
        service = get_sampling_service(workspace_id)
        
        result = service.export_dataset(
            format=request.format.value,
            output_path=request.output_path,
            include_splits=request.include_splits,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        return ExportResult(
            success=True,
            format=result["format"],
            output_path=result["output_path"],
            item_count=result["item_count"],
            size_mb=result["size_mb"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/data/export/formats")
async def get_export_formats(workspace_id: str):
    """Get list of supported export formats"""
    try:
        service = get_sampling_service(workspace_id)
        formats = service.get_supported_export_formats()
        
        return {"formats": formats}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/data/exports")
async def list_exports(workspace_id: str):
    """List all exported datasets"""
    try:
        workspace_path = get_workspace_path(workspace_id)
        exports_dir = workspace_path / "exports"
        
        if not exports_dir.exists():
            return {"exports": []}
        
        exports = []
        for export_dir in exports_dir.iterdir():
            if export_dir.is_dir():
                # Calculate size
                total_size = sum(
                    f.stat().st_size for f in export_dir.rglob("*") if f.is_file()
                )
                
                exports.append({
                    "name": export_dir.name,
                    "path": str(export_dir),
                    "size_mb": round(total_size / (1024 * 1024), 2),
                })
        
        return {"exports": exports}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
