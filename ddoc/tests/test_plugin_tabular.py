"""Round-27 (Track B) — tabular EDA report plugin tests.

Closes Round 25 shape gap #2: backend's tabular EDA reports
(``{name, rows, cols, missing, summary}``) had no compatible
template in ddoc. This plugin recognizes the shape and renders a
proper EDA-styled HTML/PDF report so backend can hand off rendering
to ddoc and drop its weasyprint dependency.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ddoc_plugin_tabular.tabular_impl import (
    TabularReportPlugin,
    _looks_tabular,
    _summary_is_table,
    _summary_stat_columns,
)


# ── pure helpers ────────────────────────────────────────────────────


def test_looks_tabular_explicit_modality():
    assert _looks_tabular({"modality": "tabular", "rows": 100}) is True


def test_looks_tabular_heuristic_no_modality():
    """Heuristic recognition for envelopes without modality field."""
    assert _looks_tabular({"rows": 100, "cols": 5, "summary": {}}) is True


def test_looks_tabular_rejects_modality_eda():
    """Pure-modality EDA envelopes (vision/text/...) must NOT be
    captured by this plugin — they're rendered by ddoc's built-in."""
    assert _looks_tabular({"modality": "vision", "files_analyzed": 10}) is False


def test_looks_tabular_rejects_drift():
    assert _looks_tabular({"modality": "vision", "overall_score": 0.18}) is False


def test_looks_tabular_handles_none_and_garbage():
    assert _looks_tabular(None) is False
    assert _looks_tabular("not a dict") is False
    assert _looks_tabular({}) is False


def test_summary_is_table_dict_of_dicts():
    assert _summary_is_table({"col1": {"mean": 1.0, "std": 0.5}}) is True


def test_summary_is_table_flat_dict_rejected():
    assert _summary_is_table({"k1": 1.0, "k2": 2.0}) is False


def test_summary_is_table_empty_rejected():
    assert _summary_is_table({}) is False
    assert _summary_is_table(None) is False


def test_summary_stat_columns_orders_pandas_first():
    s = {"col1": {"mean": 1, "std": 1, "min": 0, "max": 5, "extra": "x"}}
    cols = _summary_stat_columns(s)
    # Preferred pandas order first.
    assert cols.index("mean") < cols.index("extra")
    assert cols.index("min") < cols.index("max")
    assert "extra" in cols


# ── plugin: rendering ───────────────────────────────────────────────


_BACKEND_LIKE_ENVELOPE = {
    "modality": "tabular",
    "name": "iris.csv",
    "rows": 150,
    "cols": 5,
    "missing": {"sepal_len": 0.0, "petal_len": 0.0, "species": 0.0},
    "summary": {
        "sepal_len": {"count": 150, "mean": 5.84, "std": 0.83,
                      "min": 4.3, "50%": 5.8, "max": 7.9},
        "petal_len": {"count": 150, "mean": 3.76, "std": 1.76,
                      "min": 1.0, "50%": 4.35, "max": 6.9},
    },
}


def test_plugin_renders_html_for_tabular_envelope(tmp_path: Path):
    plugin = TabularReportPlugin()
    out = tmp_path / "r.html"
    res = plugin.report_render(
        drift_result=None,
        eda_result=_BACKEND_LIKE_ENVELOPE,
        format="html",
        output_path=str(out),
        cfg={"title": "Iris EDA"},
    )
    assert res is not None
    assert res["status"] == "success"
    assert res["format"] == "html"
    assert res["renderer"] == "ddoc-plugin-tabular"
    body = out.read_text()
    # Title + dataset metadata land in the output.
    assert "Iris EDA" in body
    assert "iris.csv" in body
    assert ">150<" in body  # rows count
    # Summary table rendered with column headers (preferred pandas order).
    assert "<th>mean</th>" in body or "mean" in body
    assert "sepal_len" in body
    # Tagline brand stamp.
    assert "data doctor" in body


def test_plugin_returns_none_for_non_tabular(tmp_path: Path):
    """Pure-modality EDA envelopes flow through to the built-in
    renderer, not this plugin."""
    plugin = TabularReportPlugin()
    out = tmp_path / "r.html"
    res = plugin.report_render(
        drift_result=None,
        eda_result={"modality": "vision", "files_analyzed": 10,
                    "summary": {"blur_mean": 0.4}},
        format="html", output_path=str(out), cfg={},
    )
    assert res is None
    assert not out.exists()


def test_plugin_returns_none_for_drift(tmp_path: Path):
    plugin = TabularReportPlugin()
    out = tmp_path / "r.html"
    res = plugin.report_render(
        drift_result={"modality": "vision", "overall_score": 0.2},
        eda_result=None,
        format="html", output_path=str(out), cfg={},
    )
    assert res is None


def test_plugin_returns_none_for_unsupported_format(tmp_path: Path):
    """We don't render markdown — let ddoc's built-in handle it."""
    plugin = TabularReportPlugin()
    out = tmp_path / "r.md"
    res = plugin.report_render(
        drift_result=None,
        eda_result=_BACKEND_LIKE_ENVELOPE,
        format="md", output_path=str(out), cfg={},
    )
    assert res is None


def test_plugin_renders_pdf_for_tabular(tmp_path: Path):
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        pytest.skip("weasyprint not available")
    plugin = TabularReportPlugin()
    out = tmp_path / "r.pdf"
    res = plugin.report_render(
        drift_result=None,
        eda_result=_BACKEND_LIKE_ENVELOPE,
        format="pdf", output_path=str(out), cfg={},
    )
    assert res is not None
    assert res["format"] == "pdf"
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_plugin_renders_when_summary_is_freeform_text(tmp_path: Path):
    """Backend's older ZIP-style EDA may pass summary as a non-table
    dict or a plain string. Plugin should still render with raw
    JSON in <pre> instead of a table."""
    plugin = TabularReportPlugin()
    out = tmp_path / "r.html"
    res = plugin.report_render(
        drift_result=None,
        eda_result={"modality": "tabular", "name": "weird",
                    "rows": 10, "cols": 3,
                    "summary": "freeform text"},
        format="html", output_path=str(out), cfg={},
    )
    assert res["status"] == "success"
    assert "freeform text" in out.read_text()


def test_plugin_metadata():
    plugin = TabularReportPlugin()
    meta = plugin.ddoc_get_metadata()
    assert meta["name"] == "ddoc-plugin-tabular"
    assert "report_render" in meta["implements"]


def test_entry_point_registered():
    from importlib.metadata import entry_points
    found = [ep.name for ep in entry_points(group="ddoc")]
    assert "ddoc_tabular" in found


# ── e2e via /report/render inline mode (Round 25 + Round 27) ────────


fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def http_client():
    os.environ.pop("DDOC_API_KEY", None)
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0"))


def test_report_render_picks_up_tabular_plugin_via_inline(http_client: TestClient):
    """End-to-end: backend-shaped envelope → /report/render inline →
    HTML response uses tabular plugin's template, not built-in."""
    r = http_client.post(
        "/report/render",
        json={"envelope": _BACKEND_LIKE_ENVELOPE, "format": "html"},
    )
    assert r.status_code == 200, r.text
    assert "text/html" in r.headers["content-type"]
    body = r.text
    # Recognizable markers from our template, not the built-in eda_report.html.
    assert "iris.csv" in body
    assert ">150<" in body  # rows count
    assert "data doctor" in body  # tagline
    # Renderer header stamps the plugin's identity.
    assert r.headers.get("X-Ddoc-Renderer") == "ddoc-plugin-tabular"


def test_report_render_falls_through_for_drift_envelope(http_client: TestClient):
    """Drift envelope → built-in renderer (not tabular plugin)."""
    drift = {
        "modality": "vision", "status": "success",
        "overall_score": 0.2, "attribute_drifts": {"blur": 0.2},
    }
    r = http_client.post(
        "/report/render",
        json={"envelope": drift, "format": "html"},
    )
    assert r.status_code == 200
    # Built-in renderer was used (our X-Ddoc-Renderer stamp would
    # say "ddoc-plugin-tabular" if we'd intercepted; expect "builtin").
    assert r.headers.get("X-Ddoc-Renderer") != "ddoc-plugin-tabular"
