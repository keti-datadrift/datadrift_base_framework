"""Common utility functions for CLI commands"""
import json
from typing import Any, Dict, List, Tuple


# Plugin manager instance (lazy loading)
_pmgr = None


def get_pmgr():
    """Get or create plugin manager instance (lazy loading)"""
    global _pmgr
    if _pmgr is None:
        from ddoc.core.plugins import get_plugin_manager
        _pmgr = get_plugin_manager()
    return _pmgr


def call_hook_isolated(pm, hook_name: str, **kwargs) -> Tuple[List[Dict[str, Any]], List[Tuple[str, Exception]]]:
    """Call each implementation of ``hook_name`` separately.

    pluggy propagates the first exception out of the whole fan-out, so a
    single plugin that chokes on an input shape it does not recognize
    would silence every other plugin's answer too. Calling the
    implementations one by one lets a plugin decline an unfamiliar input
    (returning None, or raising) without hiding the one that does handle
    it.

    Mirrors pluggy's own calling convention: implementations run in
    pluggy's call order, each receives only the arguments it declares,
    and hook wrappers are skipped.

    Returns ``(results, errors)``: the non-None results, and
    ``(plugin_name, exception)`` for every implementation that raised.
    """
    caller = getattr(pm.hook, hook_name)
    results: List[Dict[str, Any]] = []
    errors: List[Tuple[str, Exception]] = []
    for impl in reversed(caller.get_hookimpls()):
        if getattr(impl, "hookwrapper", False) or getattr(impl, "wrapper", False):
            continue
        try:
            out = impl.function(*[kwargs[name] for name in impl.argnames])
        except Exception as e:  # noqa: BLE001 — one plugin must not sink the rest
            errors.append((impl.plugin_name, e))
            continue
        if out is not None:
            results.append(out)
    return results, errors


def _pretty(x: Any) -> str:
    """JSON 또는 객체를 보기 좋게 출력"""
    try:
        # ensure_ascii=False를 사용하여 한글 깨짐 방지
        return json.dumps(x, indent=2, ensure_ascii=False)
    except Exception:
        return str(x)
