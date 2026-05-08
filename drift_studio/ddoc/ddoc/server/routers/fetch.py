"""``POST /fetch`` — wraps ``ddoc fetch``."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from ..app import map_envelope_to_response
from ..auth import require_api_key
from ..runner import run
from ..schemas import FetchRequest

router = APIRouter(tags=["fetch"], dependencies=[Depends(require_api_key)])


@router.post("/fetch")
def fetch(req: FetchRequest):
    """Materialize ``source_uri`` into ``dest`` (mirror of
    ``ddoc fetch``). Plugin-extensible via ``data_source_read``
    hookspec."""
    args = [
        "fetch", req.source_uri,
        "--dest", req.dest,
        "--json",
    ]
    if req.symlink:
        args.append("--symlink")
    if req.config:
        args += ["--config", json.dumps(req.config, default=str)]
    result = run(args, require_json=True, timeout=req.timeout_sec)
    return map_envelope_to_response(result.json)
