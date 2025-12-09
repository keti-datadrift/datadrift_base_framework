"""
FiftyOne session management router
Manages FiftyOne datasets and views for workspace data exploration
Single session with dynamic dataset switching for multi-workspace support
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import json
import threading
from datetime import datetime

from pydantic import BaseModel

router = APIRouter()

WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))
FIFTYONE_PORT = int(os.getenv("FIFTYONE_PORT", "8159"))
FIFTYONE_ADDRESS = os.getenv("FIFTYONE_ADDRESS", "0.0.0.0")

# Global single session (shared across all workspaces)
_fo_session: Optional[Any] = None
_fo_lock = threading.Lock()


class LoadDatasetRequest(BaseModel):
    """Request to load a dataset into FiftyOne"""
    dataset_name: Optional[str] = None
    force_reload: bool = False


class SaveViewRequest(BaseModel):
    """Request to save a FiftyOne view"""
    view_name: str
    description: Optional[str] = None
    filter_stages: Optional[List[dict]] = None


class FiftyOneStatus(BaseModel):
    """FiftyOne server status"""
    available: bool
    url: str
    current_dataset: Optional[str] = None
    sample_count: Optional[int] = None
    message: Optional[str] = None


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


def detect_dataset_format(data_path: Path) -> str:
    """Detect the format of the dataset"""
    # Check for YOLO format
    if (data_path / "images").exists() and (data_path / "labels").exists():
        return "yolo"
    
    # Check for COCO format
    if any(data_path.glob("*.json")) and (data_path / "images").exists():
        return "coco"
    
    # Check for Pascal VOC format
    if (data_path / "Annotations").exists() and (data_path / "JPEGImages").exists():
        return "voc"
    
    # Check for image directory
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    for item in data_path.rglob("*"):
        if item.is_file() and item.suffix.lower() in image_extensions:
            return "image_directory"
    
    return "unknown"


def load_fiftyone_dataset(workspace_id: str, data_path: Path, dataset_name: str, force_reload: bool = False):
    """
    Load dataset into FiftyOne
    """
    try:
        import fiftyone as fo
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="FiftyOne is not installed. Please install it with: pip install fiftyone"
        )
    
    # Configure MongoDB connection
    mongo_uri = os.getenv("FIFTYONE_DATABASE_URI", "mongodb://fiftyone-mongo:27017")
    fo.config.database_uri = mongo_uri
    
    # Check if dataset already exists
    if dataset_name in fo.list_datasets():
        if force_reload:
            fo.delete_dataset(dataset_name)
        else:
            return fo.load_dataset(dataset_name)
    
    # Detect format and load
    format_type = detect_dataset_format(data_path)
    
    if format_type == "yolo":
        # Load YOLO dataset
        dataset = fo.Dataset(dataset_name)
        
        images_dir = data_path / "images"
        labels_dir = data_path / "labels"
        
        # Check for splits
        for split in ["train", "val", "valid", "test"]:
            split_images = images_dir / split
            split_labels = labels_dir / split
            
            if split_images.exists():
                # Load images from this split
                for img_path in split_images.iterdir():
                    if img_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
                        sample = fo.Sample(filepath=str(img_path))
                        sample.tags.append(split)
                        
                        # Try to load corresponding label
                        label_path = split_labels / f"{img_path.stem}.txt"
                        if label_path.exists():
                            sample["has_label"] = True
                        
                        dataset.add_sample(sample)
        
        # Also check root images folder
        for img_path in images_dir.iterdir():
            if img_path.is_file() and img_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
                sample = fo.Sample(filepath=str(img_path))
                dataset.add_sample(sample)
    
    elif format_type == "image_directory":
        # Load as image directory
        dataset = fo.Dataset.from_images_dir(
            str(data_path),
            name=dataset_name,
            recursive=True,
        )
    
    else:
        # Try generic image loading
        dataset = fo.Dataset(dataset_name)
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        for img_path in data_path.rglob("*"):
            if img_path.is_file() and img_path.suffix.lower() in image_extensions:
                sample = fo.Sample(filepath=str(img_path))
                # Add parent folder as tag (for splits)
                parent = img_path.parent.name
                if parent and parent != data_path.name:
                    sample.tags.append(parent)
                dataset.add_sample(sample)
    
    dataset.persistent = True
    return dataset


@router.get("/{workspace_id}/fiftyone/status", response_model=FiftyOneStatus)
async def get_fiftyone_status(workspace_id: str):
    """
    Check FiftyOne server status and current dataset
    """
    global _fo_session
    
    try:
        import fiftyone as fo
        
        # Check if global session exists and get current dataset
        if _fo_session and _fo_session.dataset:
            current_dataset = _fo_session.dataset.name
            sample_count = len(_fo_session.dataset)
        else:
            current_dataset = None
            sample_count = None
        
        return FiftyOneStatus(
            available=True,
            url="/fiftyone/",
            current_dataset=current_dataset,
            sample_count=sample_count,
            message="FiftyOne is active" + (f" (dataset: {current_dataset}, {sample_count} samples)" if current_dataset else " (no dataset loaded)")
        )
    except ImportError:
        return FiftyOneStatus(
            available=False,
            url="/fiftyone/",
            message="FiftyOne is not installed"
        )
    except Exception as e:
        return FiftyOneStatus(
            available=False,
            url="/fiftyone/",
            message=f"FiftyOne error: {str(e)}"
        )


@router.get("/{workspace_id}/fiftyone/url")
async def get_fiftyone_url(workspace_id: str):
    """
    Get the FiftyOne UI URL for iframe embedding
    """
    global _fo_session
    
    if _fo_session is None:
        raise HTTPException(
            status_code=404,
            detail="No FiftyOne session active. Please load a dataset first."
        )
    
    return {
        "url": "/fiftyone/",
        "port": FIFTYONE_PORT,
        "workspace_id": workspace_id,
        "current_dataset": _fo_session.dataset.name if _fo_session and _fo_session.dataset else None
    }


@router.post("/{workspace_id}/fiftyone/load")
async def load_workspace_dataset(workspace_id: str, request: LoadDatasetRequest, background_tasks: BackgroundTasks):
    """
    Load workspace data into FiftyOne
    Reuses existing session if available, or creates new one
    """
    workspace_path = get_workspace_path(workspace_id)
    
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    data_path = get_workspace_data_path(workspace_id)
    
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="No data found in workspace")
    
    dataset_name = request.dataset_name or f"workspace_{workspace_id}"
    
    try:
        import fiftyone as fo
        
        # Load dataset
        dataset = load_fiftyone_dataset(
            workspace_id,
            data_path,
            dataset_name,
            force_reload=request.force_reload
        )
        
        # Switch dataset in background
        def switch_dataset():
            global _fo_session
            with _fo_lock:
                # Check if session exists
                if _fo_session is None:
                    # First time: create new session
                    print(f"[FiftyOne] Creating new session on port {FIFTYONE_PORT}")
                    _fo_session = fo.launch_app(
                        dataset,
                        remote=True,
                        address=FIFTYONE_ADDRESS,
                        port=FIFTYONE_PORT,
                    )
                else:
                    # Session exists: just switch dataset
                    print(f"[FiftyOne] Switching dataset to {dataset_name}")
                    _fo_session.dataset = dataset
        
        background_tasks.add_task(switch_dataset)
        
        return {
            "success": True,
            "dataset_name": dataset_name,
            "sample_count": len(dataset),
            "data_path": str(data_path),
            "format": detect_dataset_format(data_path),
            "fiftyone_url": "/fiftyone/",
            "message": f"Dataset '{dataset_name}' loaded with {len(dataset)} samples."
        }
    
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="FiftyOne is not installed"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load dataset: {str(e)}"
        )


@router.post("/{workspace_id}/fiftyone/close")
async def close_fiftyone_session(workspace_id: str):
    """
    Close the global FiftyOne session
    """
    global _fo_session
    
    with _fo_lock:
        if _fo_session:
            try:
                _fo_session.close()
                _fo_session = None
                return {"success": True, "message": "Session closed"}
            except Exception as e:
                return {"success": False, "message": str(e)}
    
    return {"success": False, "message": "No active session"}


@router.get("/{workspace_id}/fiftyone/views")
async def list_saved_views(workspace_id: str):
    """
    List saved FiftyOne views for this workspace
    """
    workspace_path = get_workspace_path(workspace_id)
    views_file = workspace_path / ".ddoc" / "fiftyone_views.json"
    
    views = []
    
    # Load from file
    if views_file.exists():
        with open(views_file, 'r') as f:
            views_data = json.load(f)
        views = views_data.get("views", [])
    
    # Also check FiftyOne saved views
    try:
        import fiftyone as fo
        dataset_name = f"workspace_{workspace_id}"
        
        if dataset_name in fo.list_datasets():
            dataset = fo.load_dataset(dataset_name)
            for view_name in dataset.list_saved_views():
                if not any(v["name"] == view_name for v in views):
                    views.append({
                        "name": view_name,
                        "description": "FiftyOne saved view",
                        "source": "fiftyone",
                        "created_at": None
                    })
    except:
        pass
    
    return {"views": views}


@router.post("/{workspace_id}/fiftyone/save-view")
async def save_view(workspace_id: str, request: SaveViewRequest):
    """
    Save current FiftyOne view
    """
    workspace_path = get_workspace_path(workspace_id)
    
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    # Try to save in FiftyOne first
    try:
        import fiftyone as fo
        dataset_name = f"workspace_{workspace_id}"
        
        if dataset_name in fo.list_datasets():
            dataset = fo.load_dataset(dataset_name)
            
            # Get current session view if available
            if workspace_id in _fo_sessions:
                session = _fo_sessions[workspace_id]
                if session.view is not None:
                    dataset.save_view(request.view_name, session.view)
    except Exception as e:
        print(f"[WARNING] Could not save FiftyOne view: {e}")
    
    # Also save to file for persistence
    views_file = workspace_path / ".ddoc" / "fiftyone_views.json"
    views_file.parent.mkdir(parents=True, exist_ok=True)
    
    if views_file.exists():
        with open(views_file, 'r') as f:
            views_data = json.load(f)
    else:
        views_data = {"views": []}
    
    new_view = {
        "name": request.view_name,
        "description": request.description,
        "filter_stages": request.filter_stages,
        "created_at": datetime.now().isoformat(),
    }
    
    # Update or add
    existing_idx = next((i for i, v in enumerate(views_data["views"]) if v["name"] == request.view_name), None)
    if existing_idx is not None:
        views_data["views"][existing_idx] = new_view
    else:
        views_data["views"].append(new_view)
    
    with open(views_file, 'w') as f:
        json.dump(views_data, f, indent=2)
    
    return {
        "success": True,
        "view_name": request.view_name,
        "message": f"View '{request.view_name}' saved"
    }


@router.delete("/{workspace_id}/fiftyone/views/{view_name}")
async def delete_view(workspace_id: str, view_name: str):
    """
    Delete a saved FiftyOne view
    """
    workspace_path = get_workspace_path(workspace_id)
    
    # Delete from FiftyOne
    try:
        import fiftyone as fo
        dataset_name = f"workspace_{workspace_id}"
        
        if dataset_name in fo.list_datasets():
            dataset = fo.load_dataset(dataset_name)
            if view_name in dataset.list_saved_views():
                dataset.delete_saved_view(view_name)
    except:
        pass
    
    # Delete from file
    views_file = workspace_path / ".ddoc" / "fiftyone_views.json"
    
    if views_file.exists():
        with open(views_file, 'r') as f:
            views_data = json.load(f)
        
        original_count = len(views_data["views"])
        views_data["views"] = [v for v in views_data["views"] if v["name"] != view_name]
        
        with open(views_file, 'w') as f:
            json.dump(views_data, f, indent=2)
        
        if len(views_data["views"]) < original_count:
            return {"success": True, "message": f"View '{view_name}' deleted"}
    
    raise HTTPException(status_code=404, detail=f"View '{view_name}' not found")


@router.get("/{workspace_id}/fiftyone/datasets")
async def list_datasets():
    """
    List all FiftyOne datasets
    """
    try:
        import fiftyone as fo
        return {"datasets": fo.list_datasets()}
    except ImportError:
        return {"datasets": [], "error": "FiftyOne not installed"}
