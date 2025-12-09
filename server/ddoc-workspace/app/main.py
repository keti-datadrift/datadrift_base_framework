"""
ddoc-workspace: FastAPI service for workspace management
Integrates ddoc core functionality with REST API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from .routers import workspace, snapshot, analysis, sampling, experiment, fiftyone_ops, data_ops

# Configuration from environment
WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5050")

# Ensure workspaces directory exists
WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="ddoc Workspace API",
    description="REST API for ddoc workspace management - analysis, sampling, experiments, and snapshots",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
app.include_router(snapshot.router, prefix="/workspace", tags=["snapshot"])
app.include_router(analysis.router, prefix="/workspace", tags=["analysis"])
app.include_router(sampling.router, prefix="/workspace", tags=["sampling"])
app.include_router(experiment.router, prefix="/workspace", tags=["experiment"])
app.include_router(fiftyone_ops.router, prefix="/workspace", tags=["fiftyone"])
app.include_router(data_ops.router, prefix="/workspace", tags=["data_ops"])


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "ddoc-workspace",
        "workspaces_root": str(WORKSPACES_ROOT),
        "mlflow_uri": MLFLOW_TRACKING_URI,
    }


@app.get("/health")
def health():
    """Health check for container orchestration"""
    return {"status": "healthy"}
