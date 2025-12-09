"""
Analysis router
Integrates with ddoc-plugin-vision for embedding and attribute analysis
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from typing import Optional, Dict, Any
import os
import json
from datetime import datetime

from ..schemas import (
    AnalysisRequest,
    EmbeddingAnalysisParams,
    AttributeAnalysisParams,
    AnalysisResult,
    SuccessResponse,
)

# ddoc services are installed via wheel (no sys.path manipulation needed)

router = APIRouter()

WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))


def get_workspace_path(workspace_id: str) -> Path:
    """Get full path to workspace directory"""
    return WORKSPACES_ROOT / workspace_id


def get_data_path(workspace_id: str) -> Path:
    """Get data directory path for workspace"""
    workspace_path = get_workspace_path(workspace_id)
    data_dir = workspace_path / "data"
    if not data_dir.exists():
        raise HTTPException(status_code=404, detail=f"Data directory not found in workspace {workspace_id}")
    
    # Return first subdirectory in data (the actual dataset)
    subdirs = [d for d in data_dir.iterdir() if d.is_dir()]
    if subdirs:
        return subdirs[0]
    return data_dir


def get_cache_dir(workspace_id: str) -> Path:
    """Get cache directory for analysis results"""
    workspace_path = get_workspace_path(workspace_id)
    cache_dir = workspace_path / ".ddoc" / "cache" / "analysis"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def load_cached_result(workspace_id: str, analysis_type: str) -> Optional[Dict[str, Any]]:
    """Load cached analysis result"""
    cache_file = get_cache_dir(workspace_id) / f"{analysis_type}.json"
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)
    return None


def save_cached_result(workspace_id: str, analysis_type: str, result: Dict[str, Any]):
    """Save analysis result to cache"""
    cache_file = get_cache_dir(workspace_id) / f"{analysis_type}.json"
    with open(cache_file, 'w') as f:
        json.dump(result, f, indent=2)


@router.post("/{workspace_id}/analyze/embedding", response_model=AnalysisResult)
async def analyze_embedding(
    workspace_id: str,
    params: EmbeddingAnalysisParams = EmbeddingAnalysisParams(),
    force: bool = False,
):
    """
    Run embedding analysis on workspace dataset.
    
    Uses ddoc-plugin-vision EmbeddingAnalyzer to compute:
    - Image embeddings using specified model (dinov2, clip, resnet)
    - Embedding statistics and distributions
    """
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    try:
        # Check cache
        if not force:
            cached = load_cached_result(workspace_id, "embedding")
            if cached:
                return AnalysisResult(
                    workspace_id=workspace_id,
                    analysis_type="embedding",
                    status="completed",
                    cached=True,
                    result=cached,
                )
        
        # Import and run embedding analyzer
        try:
            from ddoc_plugin_vision.data_utils.embedding_analyzer import EmbeddingAnalyzer
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail=f"ddoc-plugin-vision not available: {e}"
            )
        
        data_path = get_data_path(workspace_id)
        
        # Initialize analyzer
        analyzer = EmbeddingAnalyzer(
            dataset_path=str(data_path),
            model_name=params.model,
        )
        
        # Run analysis
        result = analyzer.analyze()
        
        # Cache result
        save_cached_result(workspace_id, "embedding", result)
        
        return AnalysisResult(
            workspace_id=workspace_id,
            analysis_type="embedding",
            status="completed",
            cached=False,
            result=result,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return AnalysisResult(
            workspace_id=workspace_id,
            analysis_type="embedding",
            status="failed",
            cached=False,
            error=str(e),
        )


@router.post("/{workspace_id}/analyze/attributes", response_model=AnalysisResult)
async def analyze_attributes(
    workspace_id: str,
    params: AttributeAnalysisParams = AttributeAnalysisParams(),
    force: bool = False,
):
    """
    Run attribute analysis on workspace dataset.
    
    Uses ddoc-plugin-vision AttributeAnalyzer to compute:
    - Image size statistics
    - Noise levels
    - Sharpness metrics
    - Brightness distribution
    """
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    try:
        # Check cache
        if not force:
            cached = load_cached_result(workspace_id, "attributes")
            if cached:
                return AnalysisResult(
                    workspace_id=workspace_id,
                    analysis_type="attributes",
                    status="completed",
                    cached=True,
                    result=cached,
                )
        
        # Import and run attribute analyzer
        try:
            from ddoc_plugin_vision.data_utils.attribute_analyzer import AttributeAnalyzer
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail=f"ddoc-plugin-vision not available: {e}"
            )
        
        data_path = get_data_path(workspace_id)
        
        # Initialize analyzer
        analyzer = AttributeAnalyzer(dataset_path=str(data_path))
        
        # Run analysis
        result = analyzer.analyze()
        
        # Cache result
        save_cached_result(workspace_id, "attributes", result)
        
        return AnalysisResult(
            workspace_id=workspace_id,
            analysis_type="attributes",
            status="completed",
            cached=False,
            result=result,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return AnalysisResult(
            workspace_id=workspace_id,
            analysis_type="attributes",
            status="failed",
            cached=False,
            error=str(e),
        )


@router.get("/{workspace_id}/analysis/results")
async def get_analysis_results(workspace_id: str):
    """Get all cached analysis results for workspace"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    results = {}
    
    # Load embedding result
    embedding_result = load_cached_result(workspace_id, "embedding")
    if embedding_result:
        results["embedding"] = {
            "status": "available",
            "cached_at": embedding_result.get("analyzed_at"),
            "summary": embedding_result.get("summary", {}),
        }
    else:
        results["embedding"] = {"status": "not_computed"}
    
    # Load attribute result
    attributes_result = load_cached_result(workspace_id, "attributes")
    if attributes_result:
        results["attributes"] = {
            "status": "available",
            "cached_at": attributes_result.get("analyzed_at"),
            "summary": attributes_result.get("summary", {}),
        }
    else:
        results["attributes"] = {"status": "not_computed"}
    
    return {
        "workspace_id": workspace_id,
        "results": results,
    }


@router.get("/{workspace_id}/analysis/{analysis_type}")
async def get_analysis_result(workspace_id: str, analysis_type: str):
    """Get specific analysis result"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    if analysis_type not in ["embedding", "attributes"]:
        raise HTTPException(status_code=400, detail=f"Unknown analysis type: {analysis_type}")
    
    result = load_cached_result(workspace_id, analysis_type)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No {analysis_type} analysis result found. Run analysis first."
        )
    
    return AnalysisResult(
        workspace_id=workspace_id,
        analysis_type=analysis_type,
        status="completed",
        cached=True,
        result=result,
    )


@router.delete("/{workspace_id}/analysis/cache", response_model=SuccessResponse)
async def clear_analysis_cache(workspace_id: str):
    """Clear all cached analysis results"""
    workspace_path = get_workspace_path(workspace_id)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
    
    cache_dir = get_cache_dir(workspace_id)
    
    # Remove all cached files
    for cache_file in cache_dir.glob("*.json"):
        cache_file.unlink()
    
    return SuccessResponse(
        success=True,
        message=f"Analysis cache cleared for workspace {workspace_id}"
    )
