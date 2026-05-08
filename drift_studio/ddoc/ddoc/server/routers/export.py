"""``POST /export/drift-report`` — wraps ``ddoc export drift-report``."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from ..app import map_envelope_to_response
from ..auth import require_api_key
from ..runner import run
from ..schemas import ExportDriftReportRequest

router = APIRouter(tags=["export"], dependencies=[Depends(require_api_key)])


@router.post("/export/drift-report")
def export_drift_report(req: ExportDriftReportRequest):
    """Ship a drift envelope to an external system (file / keti_veritas
    built-in, or any plugin-registered target)."""
    args = [
        "export", "drift-report", req.input,
        "--to", req.target,
        "--json",
    ]
    if req.config is not None:
        args += ["--config", json.dumps(req.config, default=str)]
    result = run(args, require_json=True, timeout=req.timeout_sec)
    return map_envelope_to_response(result.json)
