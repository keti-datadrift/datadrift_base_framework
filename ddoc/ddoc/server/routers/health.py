"""Health / metadata routes — bypass auth so monitoring works."""
from __future__ import annotations

import importlib.metadata as md
from typing import Any, Dict

from fastapi import APIRouter, Request

from ..auth import get_expected_key

router = APIRouter(tags=["health"])


def _ddoc_version() -> str:
    try:
        return md.version("ddoc")
    except md.PackageNotFoundError:
        return "unknown"


def _plugin_count() -> int:
    try:
        eps = md.entry_points(group="ddoc")
    except Exception:
        return 0
    try:
        return sum(1 for _ in eps)
    except Exception:
        return 0


@router.get("/")
def root(request: Request) -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "ddoc serve",
        "tagline": "data doctor",
        "version": _ddoc_version(),
        "plugin_count": _plugin_count(),
        "auth_enabled": bool(get_expected_key()),
        "bind": getattr(request.app.state, "bind_info", "?"),
        "docs": "/docs",
    }


@router.get("/healthz")
def healthz(request: Request) -> Dict[str, Any]:
    return {
        "status": "healthy",
        "ddoc_version": _ddoc_version(),
        "tagline": "data doctor",
        "plugin_count": _plugin_count(),
        "auth_enabled": bool(get_expected_key()),
        "bind": getattr(request.app.state, "bind_info", "?"),
    }


@router.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus text-format metrics. Round 19 — bypasses auth so
    standard scrapers (Prometheus, OpenMetrics) work without keys.
    Operators who want auth on this endpoint should put it behind a
    reverse proxy with IP allowlist (see deploy.md §"보안 체크리스트")."""
    from fastapi import Response
    from ..metrics import REGISTRY
    return Response(content=REGISTRY.render(), media_type="text/plain; version=0.0.4")


@router.get("/version")
def version() -> Dict[str, Any]:
    try:
        from ddoc.plugins.hookspecs import HOOKSPEC_VERSION  # type: ignore[attr-defined]
    except Exception:
        HOOKSPEC_VERSION = "unknown"
    return {
        "ddoc": _ddoc_version(),
        "hookspec": HOOKSPEC_VERSION,
    }
