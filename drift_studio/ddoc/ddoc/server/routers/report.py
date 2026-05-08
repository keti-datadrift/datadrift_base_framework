"""``POST /report/render`` — wraps ``ddoc report render``."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..app import map_envelope_to_response
from ..auth import require_api_key
from ..runner import run
from ..schemas import ReportRenderRequest

router = APIRouter(tags=["report"], dependencies=[Depends(require_api_key)])


@router.post("/report/render")
def render_report(req: ReportRenderRequest):
    """Render a drift / EDA envelope to HTML / PDF / Markdown.

    The CLI handles plugin dispatch + built-in fallback (Jinja +
    weasyprint). The server simply forwards the request and surfaces
    the resulting envelope.
    """
    args = ["report", "render", "-i", req.input, "-o", req.out, "--json"]
    if req.format:
        args += ["--format", req.format]
    if req.title:
        args += ["--title", req.title]
    result = run(args, require_json=True, timeout=req.timeout_sec)
    return map_envelope_to_response(result.json)
