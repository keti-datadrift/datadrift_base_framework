"""API-key auth dependency for ``ddoc serve``.

Disabled by default (the server defaults to localhost-only binding).
Operators set ``DDOC_API_KEY`` env or pass ``ddoc serve --api-key``;
when set, every protected endpoint requires the ``X-API-Key`` header
to match.

Health checks (``/healthz``, ``/``) bypass auth so monitoring is
unaffected.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException


def get_expected_key() -> Optional[str]:
    """Return the configured API key, or None when auth is disabled."""
    return os.getenv("DDOC_API_KEY") or None


def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> None:
    """FastAPI dependency — raises 401 when an API key is configured
    but the request omits or mismatches it. No-op when no key is
    configured (localhost-only deployment)."""
    expected = get_expected_key()
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "error_code": "missing_or_bad_api_key",
                "message": "X-API-Key header is required when DDOC_API_KEY is set.",
            },
        )
