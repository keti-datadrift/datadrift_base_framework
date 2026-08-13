"""FastAPI application factory for ``ddoc serve``."""
from __future__ import annotations

import os
from typing import Any, Dict

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .runner import RunError


# Map ddoc CLI error codes / RunError types to HTTP status codes.
_HTTP_STATUS_BY_ERROR_CODE: Dict[str, int] = {
    "unsupported_detector": 400,
    "no_adapter_for_scheme": 400,
    "incompatible_options": 400,
    "snapshot_mode_incomplete": 400,
    "path_mode_incomplete": 400,
    "snapshot_not_found": 404,
    "snapshot_load_failed": 500,
    "cache_missing": 409,
    "no_plugin": 503,
    "empty_result": 502,
    "plugin_error": 500,
    "render_failed": 500,
    "adapter_failed": 502,
    "unsupported_target": 400,
    "fetch_failed": 500,
    "hash_mismatch": 409,
}

_HTTP_STATUS_BY_RUN_ERROR_TYPE: Dict[str, int] = {
    "timeout": 504,
    "nonzero_exit": 500,
    "invalid_json": 502,
    "empty_stdout": 502,
}


def map_run_error_to_response(err: RunError) -> JSONResponse:
    """Translate a ``RunError`` into the JSON envelope + HTTP status
    contract documented in the Round-14 plan.

    When the CLI emitted a structured error envelope on stdout
    (``status: error`` + ``error_code`` + ``message``), prefer that
    as the response body — it's the contract callers care about.
    The transport-level ``error_type`` / ``stderr_tail`` etc. live
    under ``runner_error`` for diagnostics.
    """
    transport = err.to_dict()
    code = None
    if err.json_partial:
        code = err.json_partial.get("error_code")
    status = (
        _HTTP_STATUS_BY_ERROR_CODE.get(code or "")
        or _HTTP_STATUS_BY_RUN_ERROR_TYPE.get(err.error_type, 500)
    )
    if err.json_partial and isinstance(err.json_partial, dict):
        body = dict(err.json_partial)
        body.setdefault("status", "error")
        body["runner_error"] = {
            k: v for k, v in transport.items()
            if k not in ("error_envelope",)
        }
    else:
        body = transport
    return JSONResponse(status_code=status, content=body)


def map_envelope_to_response(envelope: Dict[str, Any]) -> JSONResponse:
    """Translate a CLI envelope (success or in-band error) to an HTTP
    response. ddoc CLI convention: ``status: error`` + ``error_code``
    even on exit 0 in some paths."""
    if isinstance(envelope, dict) and envelope.get("status") == "error":
        code = envelope.get("error_code", "")
        status = _HTTP_STATUS_BY_ERROR_CODE.get(code, 500)
        return JSONResponse(status_code=status, content=envelope)
    return JSONResponse(status_code=200, content=envelope)


def create_app(*, bind_info: str = "127.0.0.1:8765") -> FastAPI:
    """Build the FastAPI app. ``bind_info`` is informational only —
    propagated into ``/healthz`` so operators can confirm what they're
    talking to."""
    app = FastAPI(
        title="ddoc serve",
        description=(
            "REST facade for the ddoc CLI — every analyze / report / "
            "export / examples / fetch / plugin command, exposed as "
            "HTTP. Coexists with `drift_studio/backend` (port 8000)."
        ),
        version="0.1.0",
    )
    app.state.bind_info = bind_info

    # Round 19 — install request-level metrics middleware before
    # routers so even health-check / static-asset GETs are counted.
    from .metrics import install_middleware
    install_middleware(app)

    # Register routers (lazy-imported so optional FastAPI/uvicorn deps
    # don't cripple core ddoc imports).
    from .routers import (
        analyze, commands as commands_router, examples,
        export as export_router, fetch as fetch_router,
        health, plugins, recipe as recipe_router,
        recipes_lib, report as report_router,
    )

    # Round 15 — mount the GUI before any router that could claim
    # ``/``. FastAPI matches routes in registration order, so the GUI
    # ``/`` must be registered first to win over health.router's
    # legacy JSON-metadata ``/``. When the static dir is missing
    # (dev checkout without reinstall), we skip the override and the
    # health router's JSON ``/`` stays as the fallback.
    static_dir = Path(__file__).resolve().parent / "static"
    index_html = static_dir / "index.html"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    if index_html.exists():
        @app.get("/", include_in_schema=False)
        def _index() -> FileResponse:  # noqa: D401
            return FileResponse(str(index_html), media_type="text/html")

    app.include_router(health.router)
    app.include_router(commands_router.router)
    app.include_router(plugins.router)
    app.include_router(examples.router)
    app.include_router(analyze.router)
    app.include_router(report_router.router)
    app.include_router(export_router.router)
    app.include_router(fetch_router.router)
    app.include_router(recipe_router.router)
    app.include_router(recipes_lib.router)

    @app.exception_handler(RunError)
    async def _run_error_handler(request: Request, exc: RunError):  # noqa: ARG001
        return map_run_error_to_response(exc)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):  # noqa: ARG001
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "error_code": "invalid_request",
                "message": "request body failed validation",
                "errors": exc.errors(),
            },
        )

    return app
