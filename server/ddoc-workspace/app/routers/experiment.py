"""
Experiment router
Integrates with ddoc MLflowExperimentService for training experiments
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pathlib import Path
from typing import Optional, List
import os
import json
import shutil
from datetime import datetime

from ..schemas import (
    CodeUploadResponse,
    CodeTemplate,
    ExperimentRunRequest,
    ExperimentInfo,
    ExperimentListResponse,
    SuccessResponse,
)

# ddoc services are installed via wheel (no sys.path manipulation needed)

router = APIRouter()

WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5050")


def get_workspace_path(workspace_id: str) -> Path:
    """Get full path to workspace directory"""
    return WORKSPACES_ROOT / workspace_id


def get_code_dir(workspace_id: str) -> Path:
    """Get code directory for workspace"""
    code_dir = get_workspace_path(workspace_id) / "code"
    code_dir.mkdir(parents=True, exist_ok=True)
    return code_dir


def get_experiments_dir(workspace_id: str) -> Path:
    """Get experiments directory for workspace"""
    exp_dir = get_workspace_path(workspace_id) / "experiments"
    exp_dir.mkdir(parents=True, exist_ok=True)
    return exp_dir


def load_experiment_metadata(workspace_id: str, exp_id: str) -> Optional[dict]:
    """Load experiment metadata from JSON file"""
    metadata_file = get_experiments_dir(workspace_id) / exp_id / "ddoc_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return None


def save_experiment_metadata(workspace_id: str, exp_id: str, metadata: dict):
    """Save experiment metadata to JSON file"""
    exp_dir = get_experiments_dir(workspace_id) / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = exp_dir / "ddoc_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def update_workspace_experiment_count(workspace_id: str, count: int):
    """Update experiment count in workspace metadata"""
    workspace_path = get_workspace_path(workspace_id)
    metadata_file = workspace_path / ".ddoc" / "workspace_meta.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        metadata["experiment_count"] = count
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)


# ===========================================
# Code Management
# ===========================================

@router.post("/{workspace_id}/code/upload", response_model=CodeUploadResponse)
async def upload_trainer_code(
    workspace_id: str,
    file: UploadFile = File(...),
):
    """
    Upload trainer code file.
    
    The code should follow ddoc trainer guidelines.
    """
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    try:
        code_dir = get_code_dir(workspace_id)
        
        # Validate file extension
        if not file.filename.endswith('.py'):
            raise HTTPException(status_code=400, detail="Only Python files (.py) are allowed")
        
        # Save file
        file_path = code_dir / file.filename
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        return CodeUploadResponse(
            success=True,
            filename=file.filename,
            path=str(file_path),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/code/files")
async def list_code_files(workspace_id: str):
    """List uploaded code files"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    code_dir = get_code_dir(workspace_id)
    
    files = []
    for py_file in code_dir.glob("*.py"):
        files.append({
            "filename": py_file.name,
            "path": str(py_file),
            "size_bytes": py_file.stat().st_size,
            "modified_at": datetime.fromtimestamp(py_file.stat().st_mtime).isoformat(),
        })
    
    return {"files": files}


@router.get("/{workspace_id}/code/file/{filename}")
async def get_code_file(workspace_id: str, filename: str):
    """Get content of a code file"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    code_dir = get_code_dir(workspace_id)
    file_path = code_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    return {
        "filename": filename,
        "content": content,
    }


@router.delete("/{workspace_id}/code/file/{filename}", response_model=SuccessResponse)
async def delete_code_file(workspace_id: str, filename: str):
    """Delete a code file"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    code_dir = get_code_dir(workspace_id)
    file_path = code_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    file_path.unlink()
    
    return SuccessResponse(
        success=True,
        message=f"File {filename} deleted"
    )


@router.get("/{workspace_id}/code/templates", response_model=List[CodeTemplate])
async def get_code_templates(workspace_id: str):
    """
    Get trainer code templates.
    
    Provides starter templates for common training scenarios.
    """
    templates = [
        CodeTemplate(
            name="YOLO Object Detection",
            description="Train YOLOv8 model for object detection",
            filename="train_yolo.py",
            content='''"""
YOLO Object Detection Trainer
ddoc-compatible training script
"""
from ultralytics import YOLO
import mlflow
import os

# MLflow tracking
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5050"))
mlflow.set_experiment("ddoc")

def train(
    data_yaml: str,
    model: str = "yolov8n.pt",
    epochs: int = 100,
    batch: int = 16,
    imgsz: int = 640,
    device: str = "cpu",
    **kwargs
):
    """
    Train YOLO model.
    
    Args:
        data_yaml: Path to data.yaml file
        model: Base model to use
        epochs: Number of training epochs
        batch: Batch size
        imgsz: Image size
        device: Training device (cpu, 0, 1, etc.)
    """
    with mlflow.start_run():
        # Log parameters
        mlflow.log_params({
            "model": model,
            "epochs": epochs,
            "batch": batch,
            "imgsz": imgsz,
            "device": device,
        })
        
        # Initialize model
        yolo = YOLO(model)
        
        # Train
        results = yolo.train(
            data=data_yaml,
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
            device=device,
            project="experiments",
            name="yolo_run",
            exist_ok=True,
        )
        
        # Log metrics
        if hasattr(results, 'results_dict'):
            for key, value in results.results_dict.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key.replace("/", "_"), value)
        
        return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to data.yaml")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    
    args = parser.parse_args()
    train(
        data_yaml=args.data,
        model=args.model,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
    )
''',
        ),
        CodeTemplate(
            name="Image Classification",
            description="Train image classifier using torchvision",
            filename="train_classifier.py",
            content='''"""
Image Classification Trainer
ddoc-compatible training script using PyTorch
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
import mlflow
import os

# MLflow tracking
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5050"))
mlflow.set_experiment("ddoc")

def train(
    data_dir: str,
    model_name: str = "resnet18",
    epochs: int = 10,
    batch_size: int = 32,
    lr: float = 0.001,
    device: str = "cpu",
    **kwargs
):
    """
    Train image classifier.
    
    Args:
        data_dir: Path to dataset (should have train/val subdirectories)
        model_name: Model architecture (resnet18, resnet50, etc.)
        epochs: Number of training epochs
        batch_size: Batch size
        lr: Learning rate
        device: Training device
    """
    # Data transforms
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # Load datasets
    train_dataset = datasets.ImageFolder(f"{data_dir}/train", transform=transform)
    val_dataset = datasets.ImageFolder(f"{data_dir}/val", transform=transform)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    num_classes = len(train_dataset.classes)
    
    # Initialize model
    model = getattr(models, model_name)(pretrained=True)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    model = model.to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    with mlflow.start_run():
        mlflow.log_params({
            "model": model_name,
            "epochs": epochs,
            "batch_size": batch_size,
            "lr": lr,
            "num_classes": num_classes,
        })
        
        best_acc = 0.0
        
        for epoch in range(epochs):
            # Training
            model.train()
            running_loss = 0.0
            
            for inputs, labels in train_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                
                running_loss += loss.item()
            
            # Validation
            model.eval()
            correct = 0
            total = 0
            
            with torch.no_grad():
                for inputs, labels in val_loader:
                    inputs, labels = inputs.to(device), labels.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    total += labels.size(0)
                    correct += (predicted == labels).sum().item()
            
            val_acc = correct / total
            avg_loss = running_loss / len(train_loader)
            
            mlflow.log_metrics({
                "train_loss": avg_loss,
                "val_accuracy": val_acc,
            }, step=epoch)
            
            print(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}, Val Acc: {val_acc:.4f}")
            
            if val_acc > best_acc:
                best_acc = val_acc
                torch.save(model.state_dict(), "best_model.pth")
        
        mlflow.log_metric("best_accuracy", best_acc)
        mlflow.log_artifact("best_model.pth")
        
        return {"best_accuracy": best_acc}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to dataset")
    parser.add_argument("--model", default="resnet18")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--device", default="cpu")
    
    args = parser.parse_args()
    train(
        data_dir=args.data,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        device=args.device,
    )
''',
        ),
        CodeTemplate(
            name="Custom Trainer Base",
            description="Base template for custom training scripts",
            filename="train_custom.py",
            content='''"""
Custom Trainer Template
ddoc-compatible training script
"""
import mlflow
import os
from pathlib import Path

# MLflow tracking
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5050"))
mlflow.set_experiment("ddoc")

def train(
    data_path: str,
    **params
):
    """
    Custom training function.
    
    Implement your training logic here.
    Use MLflow to log parameters, metrics, and artifacts.
    
    Args:
        data_path: Path to dataset
        **params: Additional training parameters
    """
    with mlflow.start_run():
        # Log parameters
        mlflow.log_params(params)
        
        # =====================
        # Your training code here
        # =====================
        
        # Example: Load data
        # data = load_data(data_path)
        
        # Example: Train model
        # model = YourModel()
        # for epoch in range(epochs):
        #     loss = model.train_step(data)
        #     mlflow.log_metric("loss", loss, step=epoch)
        
        # Example: Evaluate
        # metrics = model.evaluate(data)
        # mlflow.log_metrics(metrics)
        
        # Example: Save model
        # model.save("model.pt")
        # mlflow.log_artifact("model.pt")
        
        # =====================
        
        print("Training completed!")
        
        return {"status": "completed"}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to dataset")
    # Add your custom arguments here
    
    args = parser.parse_args()
    train(data_path=args.data)
''',
        ),
    ]
    
    return templates


# ===========================================
# Experiment Execution
# ===========================================

@router.post("/{workspace_id}/experiment/run", response_model=ExperimentInfo)
async def run_experiment(
    workspace_id: str,
    request: ExperimentRunRequest,
    background_tasks: BackgroundTasks,
):
    """
    Run a training experiment.
    
    Executes the specified trainer script with given parameters.
    Results are tracked via MLflow.
    """
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    try:
        # Validate trainer script exists
        code_dir = get_code_dir(workspace_id)
        trainer_path = code_dir / request.trainer_script
        
        if not trainer_path.exists():
            raise HTTPException(status_code=404, detail=f"Trainer script {request.trainer_script} not found")
        
        # Generate experiment ID
        exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get dataset path
        data_dir = workspace_path / "data"
        data_subdirs = [d for d in data_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        dataset_path = data_subdirs[0] if data_subdirs else data_dir
        
        # Find data.yaml if exists
        data_yaml = None
        for yaml_file in dataset_path.rglob("data.yaml"):
            data_yaml = str(yaml_file)
            break
        
        # Create experiment metadata
        metadata = {
            "experiment_id": exp_id,
            "name": request.name,
            "workspace_id": workspace_id,
            "trainer_script": request.trainer_script,
            "params": request.params,
            "dataset_path": str(dataset_path),
            "data_yaml": data_yaml,
            "dataset_version": request.dataset_version,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "mlflow_tracking_uri": MLFLOW_TRACKING_URI,
        }
        
        save_experiment_metadata(workspace_id, exp_id, metadata)
        
        # Run experiment in background
        background_tasks.add_task(
            _run_experiment_task,
            workspace_id=workspace_id,
            exp_id=exp_id,
            trainer_path=str(trainer_path),
            params=request.params,
            data_path=str(dataset_path),
            data_yaml=data_yaml,
        )
        
        # Update experiment count
        exp_dir = get_experiments_dir(workspace_id)
        exp_count = len([d for d in exp_dir.iterdir() if d.is_dir()])
        update_workspace_experiment_count(workspace_id, exp_count)
        
        return ExperimentInfo(
            experiment_id=exp_id,
            mlflow_run_id=None,
            name=request.name,
            status="running",
            dataset_version=request.dataset_version or "current",
            params=request.params,
            metrics={},
            created_at=metadata["created_at"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_experiment_task(
    workspace_id: str,
    exp_id: str,
    trainer_path: str,
    params: dict,
    data_path: str,
    data_yaml: str = None,
):
    """Background task to run experiment"""
    import subprocess
    
    try:
        # Build command
        cmd = ["python", trainer_path]
        
        # Add data path
        if data_yaml:
            cmd.extend(["--data", data_yaml])
        else:
            cmd.extend(["--data", data_path])
        
        # Add other parameters
        for key, value in params.items():
            cmd.extend([f"--{key}", str(value)])
        
        # Set environment
        env = os.environ.copy()
        env["MLFLOW_TRACKING_URI"] = MLFLOW_TRACKING_URI
        
        # Run trainer
        result = subprocess.run(
            cmd,
            cwd=str(get_workspace_path(workspace_id)),
            capture_output=True,
            text=True,
            env=env,
        )
        
        # Update metadata
        metadata = load_experiment_metadata(workspace_id, exp_id) or {}
        
        if result.returncode == 0:
            metadata["status"] = "completed"
            metadata["completed_at"] = datetime.now().isoformat()
        else:
            metadata["status"] = "failed"
            metadata["error"] = result.stderr
        
        metadata["stdout"] = result.stdout
        metadata["stderr"] = result.stderr
        
        save_experiment_metadata(workspace_id, exp_id, metadata)
        
    except Exception as e:
        # Update metadata with error
        metadata = load_experiment_metadata(workspace_id, exp_id) or {}
        metadata["status"] = "failed"
        metadata["error"] = str(e)
        save_experiment_metadata(workspace_id, exp_id, metadata)


# ===========================================
# Experiment Queries
# ===========================================

@router.get("/{workspace_id}/experiments", response_model=ExperimentListResponse)
async def list_experiments(workspace_id: str):
    """List all experiments for workspace"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    exp_dir = get_experiments_dir(workspace_id)
    
    experiments = []
    for exp_subdir in exp_dir.iterdir():
        if exp_subdir.is_dir():
            metadata = load_experiment_metadata(workspace_id, exp_subdir.name)
            if metadata:
                experiments.append(ExperimentInfo(
                    experiment_id=metadata.get("experiment_id", exp_subdir.name),
                    mlflow_run_id=metadata.get("mlflow_run_id"),
                    name=metadata.get("name", exp_subdir.name),
                    status=metadata.get("status", "unknown"),
                    dataset_version=metadata.get("dataset_version", "unknown"),
                    params=metadata.get("params", {}),
                    metrics=metadata.get("metrics", {}),
                    created_at=metadata.get("created_at", ""),
                    completed_at=metadata.get("completed_at"),
                ))
    
    # Sort by creation time (newest first)
    experiments.sort(key=lambda x: x.created_at, reverse=True)
    
    return ExperimentListResponse(
        experiments=experiments,
        total=len(experiments),
    )


@router.get("/{workspace_id}/experiment/{exp_id}", response_model=ExperimentInfo)
async def get_experiment(workspace_id: str, exp_id: str):
    """Get details of a specific experiment"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    metadata = load_experiment_metadata(workspace_id, exp_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found")
    
    return ExperimentInfo(
        experiment_id=metadata.get("experiment_id", exp_id),
        mlflow_run_id=metadata.get("mlflow_run_id"),
        name=metadata.get("name", exp_id),
        status=metadata.get("status", "unknown"),
        dataset_version=metadata.get("dataset_version", "unknown"),
        params=metadata.get("params", {}),
        metrics=metadata.get("metrics", {}),
        created_at=metadata.get("created_at", ""),
        completed_at=metadata.get("completed_at"),
    )


@router.get("/{workspace_id}/experiment/{exp_id}/logs")
async def get_experiment_logs(workspace_id: str, exp_id: str):
    """Get logs for an experiment"""
    metadata = load_experiment_metadata(workspace_id, exp_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found")
    
    return {
        "experiment_id": exp_id,
        "stdout": metadata.get("stdout", ""),
        "stderr": metadata.get("stderr", ""),
        "status": metadata.get("status", "unknown"),
    }


@router.delete("/{workspace_id}/experiment/{exp_id}", response_model=SuccessResponse)
async def delete_experiment(workspace_id: str, exp_id: str):
    """Delete an experiment"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    exp_dir = get_experiments_dir(workspace_id) / exp_id
    if not exp_dir.exists():
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found")
    
    shutil.rmtree(exp_dir)
    
    # Update experiment count
    all_exp_dir = get_experiments_dir(workspace_id)
    exp_count = len([d for d in all_exp_dir.iterdir() if d.is_dir()])
    update_workspace_experiment_count(workspace_id, exp_count)
    
    return SuccessResponse(
        success=True,
        message=f"Experiment {exp_id} deleted"
    )


@router.get("/{workspace_id}/mlflow/url")
async def get_mlflow_url(workspace_id: str):
    """Get MLflow tracking URL"""
    return {
        "workspace_id": workspace_id,
        "mlflow_tracking_uri": MLFLOW_TRACKING_URI,
        "mlflow_ui_url": MLFLOW_TRACKING_URI.replace(":5050", ":5050"),
    }
