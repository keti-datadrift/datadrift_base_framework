"""Round-25 — /report/render inline-envelope mode.

Round 11 's path-mode renderer required the caller to write the
envelope JSON to a filesystem path that ddoc could read, and the
output was likewise written to disk. That assumes shared FS — a
non-starter for HTTP consumers (e.g., ``drift_studio/backend``).

Round 25 adds an inline mode: POST the envelope as a dict, get the
rendered file as response bytes. This test file covers the new mode
plus the validation that the two modes are mutually exclusive."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    os.environ.pop("DDOC_API_KEY", None)
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0"))


# Minimal EDA envelope that ddoc's CLI / built-in templates accept.
# Per ``_classify_envelope`` heuristic: ``files_analyzed`` → EDA-shaped.
_EDA_ENVELOPE = {
    "modality": "vision",
    "status": "success",
    "files_analyzed": 12,
    "summary": {
        "image_count": 12,
        "blur_mean": 0.42,
    },
}

# Originally Round 25 found that the markdown renderer crashed on
# anything but a flat ``{name: float}`` dict (the natural list-of-dict
# and nested-dict shapes both broke). Round 28 (Track C) added
# ``_normalize_attribute_drifts`` so all three shapes are accepted —
# we use the list-of-dict shape here to exercise the normalization path
# end-to-end through the inline-envelope route.
_DRIFT_ENVELOPE = {
    "modality": "vision",
    "status": "success",
    "overall_score": 0.18,
    "attribute_drifts": [
        {"attribute": "blur", "score": 0.18, "status": "warning"},
        {"attribute": "exposure", "score": 0.07, "status": "ok"},
    ],
}


def test_inline_envelope_returns_html_bytes(client: TestClient):
    r = client.post(
        "/report/render",
        json={"envelope": _EDA_ENVELOPE, "format": "html"},
    )
    assert r.status_code == 200, r.text
    assert "text/html" in r.headers["content-type"]
    assert r.headers.get("X-Ddoc-Renderer")
    body = r.text
    # The built-in Jinja template stamps a recognizable string.
    assert "<html" in body.lower() or "<body" in body.lower()


def test_inline_envelope_returns_markdown(client: TestClient):
    r = client.post(
        "/report/render",
        json={"envelope": _DRIFT_ENVELOPE, "format": "md"},
    )
    assert r.status_code == 200, r.text
    assert "text/markdown" in r.headers["content-type"]
    body = r.text
    assert len(body) > 0
    # Drift envelopes get an "overall" score reference somewhere in MD.
    assert "0.18" in body or "0.180" in body or "overall" in body.lower()


def test_inline_envelope_pdf_bytes(client: TestClient):
    """PDF output round-trips raw bytes. weasyprint is part of ddoc's
    dependency set so this should work in the venv."""
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        pytest.skip("weasyprint not installed in test env")
    r = client.post(
        "/report/render",
        json={"envelope": _EDA_ENVELOPE, "format": "pdf"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    body = r.content
    assert body[:4] == b"%PDF", "expected PDF magic bytes at start of response"


def test_inline_format_required_when_no_out(client: TestClient):
    r = client.post("/report/render", json={"envelope": _EDA_ENVELOPE})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "missing_format"


def test_input_and_envelope_mutually_exclusive(client: TestClient, tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    r = client.post(
        "/report/render",
        json={"input": str(p), "envelope": _EDA_ENVELOPE, "format": "html"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_input_mode"


def test_neither_input_nor_envelope(client: TestClient):
    r = client.post("/report/render", json={"format": "html"})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_input_mode"


def test_inline_with_title_passthrough(client: TestClient):
    r = client.post(
        "/report/render",
        json={"envelope": _EDA_ENVELOPE, "format": "html", "title": "Q4 audit"},
    )
    assert r.status_code == 200, r.text
    assert "Q4 audit" in r.text


def test_path_mode_still_works(client: TestClient, tmp_path: Path):
    """Backward-compat: existing path-mode callers unaffected."""
    import json
    in_path = tmp_path / "envelope.json"
    in_path.write_text(json.dumps(_EDA_ENVELOPE))
    out_path = tmp_path / "r.html"
    r = client.post(
        "/report/render",
        json={"input": str(in_path), "out": str(out_path), "format": "html"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert out_path.exists() and out_path.stat().st_size > 0
