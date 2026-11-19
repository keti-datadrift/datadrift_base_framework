"""Common utility functions for CLI commands"""
import json
from typing import Any


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
