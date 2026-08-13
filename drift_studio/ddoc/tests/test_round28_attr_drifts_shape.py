"""Round-28 (Track C) — ``attribute_drifts`` shape tolerance.

Round 25 tests revealed that the markdown renderer's
``f"- ``{k}``: {v:.4f}"`` line crashes when ``attribute_drifts`` is a
list of dicts or a nested dict — natural shapes coming from many
real-world drift detectors. The HTML template had the same issue
silently (``"%.4f"|format(v)`` fails on dict).

Round 28 normalizes these shapes via ``_normalize_attribute_drifts``
and threads the result through both the markdown renderer and the
Jinja template via ``attribute_drifts_rows``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ddoc.cli.commands.report import _normalize_attribute_drifts


# ── normalizer (unit) ───────────────────────────────────────────────


def test_normalize_flat_dict():
    rows = _normalize_attribute_drifts({"blur": 0.18, "exposure": 0.07})
    by_name = {name: (score, extras) for name, score, extras in rows}
    assert by_name["blur"] == (0.18, {})
    assert by_name["exposure"] == (0.07, {})


def test_normalize_nested_dict_with_extras():
    rows = _normalize_attribute_drifts({
        "blur": {"score": 0.18, "status": "warning", "threshold": 0.15},
        "exposure": {"score": 0.07, "status": "ok"},
    })
    by_name = {name: (score, extras) for name, score, extras in rows}
    assert by_name["blur"][0] == 0.18
    assert by_name["blur"][1] == {"status": "warning", "threshold": 0.15}
    assert by_name["exposure"][0] == 0.07


def test_normalize_list_of_dicts():
    rows = _normalize_attribute_drifts([
        {"attribute": "blur", "score": 0.18, "status": "warning"},
        {"attribute": "exposure", "score": 0.07},
    ])
    by_name = {name: (score, extras) for name, score, extras in rows}
    assert by_name["blur"][0] == 0.18
    assert by_name["blur"][1] == {"status": "warning"}
    assert by_name["exposure"][0] == 0.07


def test_normalize_list_alt_keys():
    """Some detectors use 'name' or 'key' instead of 'attribute'."""
    rows = _normalize_attribute_drifts([
        {"name": "blur", "score": 0.18},
        {"key": "exposure", "score": 0.07},
    ])
    names = [name for name, _, _ in rows]
    assert names == ["blur", "exposure"]


def test_normalize_handles_none_and_empty():
    assert _normalize_attribute_drifts(None) == []
    assert _normalize_attribute_drifts({}) == []
    assert _normalize_attribute_drifts([]) == []


def test_normalize_handles_unknown_shape_gracefully():
    """Garbage input must not crash the renderer — return empty."""
    assert _normalize_attribute_drifts("not a dict or list") == []
    assert _normalize_attribute_drifts(42) == []


def test_normalize_score_none_when_non_numeric():
    """Score must be coerced to float or None — never raise."""
    rows = _normalize_attribute_drifts({"blur": "high"})
    assert rows[0][1] is None


# ── e2e: renderer no longer crashes on the three shapes ─────────────


fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    os.environ.pop("DDOC_API_KEY", None)
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0"))


def _drift_envelope(attribute_drifts):
    return {
        "modality": "vision",
        "status": "success",
        "overall_score": 0.18,
        "attribute_drifts": attribute_drifts,
    }


def test_markdown_render_flat_dict_shape(client: TestClient):
    """Backward-compat: original flat-dict shape still works."""
    r = client.post(
        "/report/render",
        json={
            "envelope": _drift_envelope({"blur": 0.18, "exposure": 0.07}),
            "format": "md",
        },
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "blur" in body and "0.1800" in body


def test_markdown_render_list_of_dicts_shape(client: TestClient):
    """Round 25 originally crashed here. Round 28 makes it work."""
    r = client.post(
        "/report/render",
        json={
            "envelope": _drift_envelope([
                {"attribute": "blur", "score": 0.18, "status": "warning"},
                {"attribute": "exposure", "score": 0.07, "status": "ok"},
            ]),
            "format": "md",
        },
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "blur" in body
    assert "0.1800" in body
    # extras now appear inline rather than crashing.
    assert "status=warning" in body


def test_markdown_render_nested_dict_shape(client: TestClient):
    r = client.post(
        "/report/render",
        json={
            "envelope": _drift_envelope({
                "blur": {"score": 0.18, "status": "warning"},
                "exposure": {"score": 0.07},
            }),
            "format": "md",
        },
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "blur" in body and "0.1800" in body
    assert "status=warning" in body


def test_html_render_list_of_dicts_shape(client: TestClient):
    """Same shape tolerance for the HTML/Jinja path."""
    r = client.post(
        "/report/render",
        json={
            "envelope": _drift_envelope([
                {"attribute": "blur", "score": 0.18, "status": "warning"},
            ]),
            "format": "html",
        },
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "<code>blur</code>" in body
    assert "0.1800" in body
    assert "status=warning" in body


def test_html_render_nested_dict_shape(client: TestClient):
    r = client.post(
        "/report/render",
        json={
            "envelope": _drift_envelope({
                "blur": {"score": 0.18, "status": "warning"},
            }),
            "format": "html",
        },
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "<code>blur</code>" in body
    assert "0.1800" in body


def test_render_no_attribute_drifts_section_when_empty(client: TestClient):
    """Empty / None / unrecognized → section omitted, no crash."""
    r = client.post(
        "/report/render",
        json={
            "envelope": _drift_envelope({}),
            "format": "md",
        },
    )
    assert r.status_code == 200, r.text
    body = r.text
    # Section header should not appear when there's nothing to list.
    assert "## Attribute drifts" not in body


def test_render_score_none_displayed_as_dash(client: TestClient):
    """Non-numeric score → dash placeholder, not exception."""
    r = client.post(
        "/report/render",
        json={
            "envelope": _drift_envelope({"blur": {"score": None,
                                                  "status": "missing"}}),
            "format": "md",
        },
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "blur" in body
    assert "—" in body  # em-dash placeholder
