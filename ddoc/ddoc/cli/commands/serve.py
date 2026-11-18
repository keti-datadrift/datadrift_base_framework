"""``ddoc serve`` — Round-14 FastAPI facade entry.

Spins up uvicorn with the FastAPI app from ``ddoc/server/app.py``.
Defaults to localhost-only binding. ``DDOC_API_KEY`` env (or
``--api-key``) opts into header-based auth.
"""
from __future__ import annotations

import os
from typing import Optional

import typer
from rich import print as rprint


def serve_command(
    host: str = typer.Option(
        "127.0.0.1", "--host",
        help="Bind address. Use 0.0.0.0 only with --api-key set (and behind TLS).",
    ),
    port: int = typer.Option(
        8765, "--port",
        help="Bind port. Default 8765 to coexist with drift_studio backend (8000).",
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key",
        help="API key required in X-API-Key header. Overrides DDOC_API_KEY env.",
    ),
    log_level: str = typer.Option(
        "info", "--log-level",
        help="uvicorn log level: debug | info | warning | error",
    ),
    reload: bool = typer.Option(
        False, "--reload",
        help="uvicorn auto-reload on code change (dev only).",
    ),
):
    """Start the ddoc REST facade.

    Examples:
        ddoc serve                                 # localhost:8765, no auth
        ddoc serve --port 8000                     # different port
        DDOC_API_KEY=secret ddoc serve             # auth via env
        ddoc serve --api-key secret                # auth via flag
        ddoc serve --host 0.0.0.0 --api-key ...    # exposed; auth REQUIRED

    Then:
        curl http://localhost:8765/healthz
        curl http://localhost:8765/docs            # Swagger UI
    """
    if api_key:
        os.environ["DDOC_API_KEY"] = api_key

    if host not in ("127.0.0.1", "localhost") and not os.getenv("DDOC_API_KEY"):
        rprint(
            "[yellow]⚠️  Binding to non-loopback host without DDOC_API_KEY set. "
            "Anyone on the network can call the API.[/yellow]"
        )

    try:
        import uvicorn
    except ImportError:
        rprint("[red]❌ uvicorn not installed (it ships with ddoc core; reinstall ddoc).[/red]")
        raise typer.Exit(code=2)

    bind = f"{host}:{port}"
    rprint(f"[cyan]🌐 ddoc serve listening on http://{bind}[/cyan]")
    rprint(
        f"[dim]   auth: {'enabled (X-API-Key required)' if os.getenv('DDOC_API_KEY') else 'disabled (localhost-only)'}\n"
        f"   docs: http://{bind}/docs[/dim]"
    )

    # Late-import the factory; create_app reads bind_info into app.state.
    from ddoc.server.app import create_app
    app = create_app(bind_info=bind)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,
        access_log=(log_level == "debug"),
    )
