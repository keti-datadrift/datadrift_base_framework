"""Workspace routers — ddoc-backed REST surface.

These routers expose ddoc core functionality (workspace, snapshot,
analysis, experiments, sampling, data ops) via REST API under
the /workspace prefix. Phase 1 cleanup (2026-05-07): the standalone
ddoc-workspace service was retired; backend is now the sole HTTP
front door for these operations.
"""

from fastapi import APIRouter

from . import workspace, snapshot, analysis, sampling, experiment, fiftyone_ops, data_ops

router = APIRouter(prefix="/workspace", tags=["workspace"])

router.include_router(workspace.router)
router.include_router(snapshot.router)
router.include_router(analysis.router)
router.include_router(sampling.router)
router.include_router(experiment.router)
router.include_router(fiftyone_ops.router)
router.include_router(data_ops.router)
