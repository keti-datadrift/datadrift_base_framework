"""Common utility functions for CLI commands"""
import json
from typing import Optional, Any, Tuple
from pathlib import Path


def load_params_yaml():
    """Load params.yaml file"""
    from rich import print
    try:
        import yaml
        with open("params.yaml", 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Warning: Could not load params.yaml: {e}")
        return {}


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


# Service instances (lazy initialization)
_core_ops = None
_metadata_service = None
_dataset_service = None
_experiment_service = None


def get_core_ops():
    """Get core_ops instance (lazy initialization)"""
    global _core_ops
    if _core_ops is None:
        from ddoc.ops.core_ops import CoreOpsPlugin
        _core_ops = CoreOpsPlugin()
    return _core_ops


def get_metadata_service_instance():
    """Get metadata service instance (lazy initialization)"""
    global _metadata_service
    if _metadata_service is None:
        from ddoc.core.metadata_service import get_metadata_service
        _metadata_service = get_metadata_service()
    return _metadata_service


def get_dataset_service_instance():
    """Get dataset service instance (lazy initialization)"""
    global _dataset_service
    if _dataset_service is None:
        from ddoc.core.dataset_service import get_dataset_service
        _dataset_service = get_dataset_service()
    return _dataset_service


def get_experiment_service_instance():
    """Get experiment service instance (lazy initialization)"""
    global _experiment_service
    if _experiment_service is None:
        from ddoc.core.experiment_service import get_experiment_service
        _experiment_service = get_experiment_service()
    return _experiment_service


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

