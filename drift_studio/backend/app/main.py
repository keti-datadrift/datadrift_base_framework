import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import datasets, eda, drift, report, files, ws, field_agents, training, model_registry

logger = logging.getLogger(__name__)

# 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Drift Studio",
    description="Unified backend — dataset analysis + workspace management + field agent hub",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dataset Analysis (existing) ─────────────────────────────
app.include_router(datasets.router)
app.include_router(eda.router)
app.include_router(drift.router)
app.include_router(files.router)
app.include_router(ws.router)

# ── Field Agent Hub (Phase B — 3-project integration) ─────
app.include_router(field_agents.router)

# ── Training Orchestration (Stage 2) ─────────────────────
app.include_router(training.router)

# ── Model Deployment (Stage 3) ───────────────────────────
app.include_router(model_registry.router)

# ── Workspace Management (ddoc-backed) ────────────────────
# Only enabled when ddoc core is installed (DDOC_ENABLED=true)
_ddoc_enabled = os.getenv("DDOC_ENABLED", "false").lower() == "true"
if _ddoc_enabled:
    try:
        from .routers.workspace import router as workspace_router
        app.include_router(workspace_router)

        # Ensure workspace root exists
        _ws_root = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))
        _ws_root.mkdir(parents=True, exist_ok=True)

        logger.info("[DD] Workspace routers enabled (root=%s)", _ws_root)
    except ImportError as e:
        logger.warning("[DD] ddoc core not installed, workspace disabled: %s", e)
else:
    logger.info("[DD] Workspace routers disabled (DDOC_ENABLED=false)")


# ── Phase 4 — DVC remote bootstrap ──────────────────────────
# Opportunistic. Backend startup never fails because of remote config —
# the setup script logs and exits 0 on its own.
@app.on_event("startup")
def _dvc_remote_bootstrap():
    if not os.getenv("DVC_REMOTE_URL"):
        return
    import subprocess
    script = Path(__file__).resolve().parent.parent / "scripts" / "dvc_remote_setup.sh"
    if not script.exists():
        logger.warning("[DVC] setup script missing: %s", script)
        return
    try:
        proc = subprocess.run(
            ["bash", str(script)],
            cwd=Path(os.getenv("DVC_WORKDIR", str(Path.cwd()))),
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0:
            logger.info("[DVC] remote bootstrap done\n%s", proc.stdout.strip())
        else:
            logger.warning(
                "[DVC] remote bootstrap returned %d\n%s\n%s",
                proc.returncode, proc.stdout, proc.stderr,
            )
    except Exception as e:
        logger.warning("[DVC] remote bootstrap failed: %s", e)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "drift-studio",
        "version": "2.0.0",
        "workspace_enabled": _ddoc_enabled,
        "ddoc_cli_orchestrator": os.getenv("BACKEND_USE_DDOC_CLI", "false").lower()
                                  in ("1", "true", "yes"),
    }


@app.get("/health")
def health():
    return {"status": "healthy"}