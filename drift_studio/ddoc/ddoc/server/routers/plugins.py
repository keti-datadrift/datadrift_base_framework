"""``/plugins`` and ``/plugins/detectors`` — plugin discovery."""
from __future__ import annotations

import importlib.metadata as md
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from ..auth import require_api_key

router = APIRouter(tags=["plugins"], dependencies=[Depends(require_api_key)])


def _classify(name: str) -> str:
    n = name.lower()
    if "vision" in n:
        return "vision"
    if "yolo" in n:
        return "object-detect"
    if "nlp" in n or "text" in n:
        return "text"
    if "audio" in n:
        return "audio"
    if "timeseries" in n or "ts" in n:
        return "timeseries"
    if "core" in n or "builtin" in n:
        return "core"
    return "extension"


@router.get("/plugins")
def list_plugins() -> Dict[str, Any]:
    """Mirror of ``ddoc plugin list`` — entry points only, no plugin
    instantiation."""
    try:
        eps = md.entry_points(group="ddoc")
    except Exception as e:
        return {"status": "error", "error_code": "registry_unavailable", "message": str(e)}
    items: List[Dict[str, str]] = []
    for ep in eps:
        items.append({"name": ep.name, "type": _classify(ep.name), "value": ep.value})
    return {"status": "ok", "count": len(items), "plugins": items}


@router.get("/plugins/detectors")
def list_detector_registry() -> Dict[str, Any]:
    """Mirror of ``ddoc plugin detectors`` — calls the
    ``ddoc_supported_detectors`` hookspec across all installed
    plugins (Round 13)."""
    try:
        from ddoc.cli.commands.utils import get_pmgr
    except Exception as e:
        return {"status": "error", "error_code": "pmgr_unavailable", "message": str(e)}
    try:
        decls = get_pmgr().pm.hook.ddoc_supported_detectors()
    except Exception as e:
        return {"status": "error", "error_code": "registry_call_failed", "message": str(e)}
    decls = [d for d in (decls or []) if isinstance(d, dict)]
    return {
        "status": "ok",
        "count": len(decls),
        "registry": decls,
    }
