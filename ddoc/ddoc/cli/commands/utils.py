"""Common utility functions for CLI commands"""
import json
from typing import Optional, Any, Tuple
from pathlib import Path


def get_dataset_path(dataset_name: str) -> Optional[str]:
    """Get dataset path using new mapping system with params.yaml fallback"""
    # Check if it's a direct path
    if Path(dataset_name).exists():
        return dataset_name
    
    # Check if it's in the data/ folder (ddoc workspace convention)
    data_path = Path("data") / dataset_name
    if data_path.exists():
        return str(data_path)
    
    # Try new mapping system
    from ddoc.core.metadata_service import get_metadata_service
    metadata_service = get_metadata_service()
    mapping = metadata_service.get_dataset_mapping(dataset_name)
    if mapping:
        return mapping.get('dataset_path')
    
    # Fallback to params.yaml (legacy support)
    params = load_params_yaml()
    dataset_config = next(
        (ds for ds in params.get('datasets', []) if ds['name'] == dataset_name),
        None
    )
    if dataset_config:
        return dataset_config['path']
    
    return None


# Plugin manager instance (lazy loading)
_pmgr = None


def get_pmgr():
    """Get or create plugin manager instance (lazy loading)"""
    global _pmgr
    if _pmgr is None:
        from ddoc.core.plugins import get_plugin_manager
        _pmgr = get_plugin_manager()
    return _pmgr


def _pretty(x: Any) -> str:
    """JSON 또는 객체를 보기 좋게 출력"""
    try:
        # ensure_ascii=False를 사용하여 한글 깨짐 방지
        return json.dumps(x, indent=2, ensure_ascii=False)
    except Exception:
        return str(x)


def _resolve_dataset_reference(dataset_ref: str) -> Tuple[str, Optional[str]]:
    """
    Resolve dataset reference in format: name or name@version/alias
    
    Args:
        dataset_ref: Dataset reference string (e.g., 'my_data' or 'my_data@v1.0' or 'my_data@best_acc')
    
    Returns:
        Tuple of (dataset_name, version_or_alias)
    """
    if '@' in dataset_ref:
        parts = dataset_ref.split('@', 1)
        return parts[0], parts[1]
    return dataset_ref, None

