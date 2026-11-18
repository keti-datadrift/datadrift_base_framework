"""``POST /report/render`` — wraps ``ddoc report render``.

Round 25 — added *inline* mode: callers can POST the envelope dict
directly (no shared filesystem needed) and receive the rendered file
as response bytes. Path mode (Round 11+) still works for callers that
already write the envelope to disk.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..app import map_envelope_to_response
from ..auth import require_api_key
from ..runner import run
from ..schemas import ReportRenderRequest

router = APIRouter(tags=["report"], dependencies=[Depends(require_api_key)])


_FORMAT_TO_CONTENT_TYPE = {
    "pdf": "application/pdf",
    "html": "text/html; charset=utf-8",
    "md": "text/markdown; charset=utf-8",
}
_FORMAT_TO_SUFFIX = {"pdf": ".pdf", "html": ".html", "md": ".md"}


def _infer_format(req: ReportRenderRequest, out: Optional[str]) -> str:
    if req.format:
        return req.format
    if out:
        suffix = Path(out).suffix.lstrip(".").lower()
        if suffix in _FORMAT_TO_SUFFIX:
            return suffix
    raise HTTPException(
        status_code=400,
        detail={
            "status": "error",
            "error_code": "missing_format",
            "message": "format is required in inline mode (or pass an out path with .pdf/.html/.md suffix).",
        },
    )


def _validate_modes(req: ReportRenderRequest) -> None:
    has_input = bool(req.input)
    has_envelope = req.envelope is not None
    if has_input == has_envelope:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "error_code": "invalid_input_mode",
                "message": "exactly one of {input, envelope} must be provided.",
            },
        )


@router.post("/report/render")
def render_report(req: ReportRenderRequest):
    """Render an envelope to HTML / PDF / Markdown.

    Path mode: ``{input: "<path>", out: "<path>", format?: "..."}`` →
    returns the JSON envelope from the CLI (``{status, format,
    output_path, size_bytes, ...}``).

    Inline mode: ``{envelope: {...}, format: "pdf"}`` → returns the
    rendered file as response bytes (Content-Type matches format).
    """
    _validate_modes(req)

    # Inline mode: write envelope to temp file, render to temp file,
    # stream the result. We keep the temp files in a TemporaryDirectory
    # so they're cleaned up even on exception paths.
    if req.envelope is not None:
        fmt = _infer_format(req, req.out)
        tmpdir = tempfile.mkdtemp(prefix="ddoc-report-inline-")
        try:
            input_path = Path(tmpdir) / "envelope.json"
            input_path.write_text(json.dumps(req.envelope), encoding="utf-8")
            out_path = req.out or str(Path(tmpdir) / f"report{_FORMAT_TO_SUFFIX[fmt]}")
            args = ["report", "render", "-i", str(input_path),
                    "-o", out_path, "--format", fmt, "--json"]
            if req.title:
                args += ["--title", req.title]
            result = run(args, require_json=True, timeout=req.timeout_sec)
            envelope_json = result.json or {}
            if envelope_json.get("status") == "error":
                # Surface CLI-level error to the caller as a regular
                # JSON envelope (same as path mode).
                return map_envelope_to_response(envelope_json)
            # Stream the file. Schedule tmpdir cleanup after response
            # is fully sent. We read the bytes upfront because the
            # tmpdir is wiped on function return.
            data = Path(out_path).read_bytes()
            content_type = _FORMAT_TO_CONTENT_TYPE.get(fmt, "application/octet-stream")
            headers = {
                "X-Ddoc-Renderer": str(envelope_json.get("renderer", "builtin")),
                "X-Ddoc-Size-Bytes": str(envelope_json.get("size_bytes", len(data))),
            }
            return StreamingResponse(
                iter([data]), media_type=content_type, headers=headers,
            )
        finally:
            # Best-effort cleanup; tempdir lives only for this request.
            import shutil
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:  # noqa: BLE001
                pass

    # Path mode (original behavior).
    args = ["report", "render", "-i", req.input, "-o", req.out, "--json"]
    if req.format:
        args += ["--format", req.format]
    if req.title:
        args += ["--title", req.title]
    result = run(args, require_json=True, timeout=req.timeout_sec)
    return map_envelope_to_response(result.json)
