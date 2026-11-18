"""End-to-end tests for the ``ddoc serve`` REST facade (Round 14).

Uses FastAPI TestClient + the toy-data factories from
``tests/fixtures/factories.py``. Each test forks ddoc CLI as a real
subprocess so the route → runner → CLI chain is exercised
end-to-end.

Heavy modality plugins (text/vision) get a graceful skip when their
deps aren't available, mirroring ``test_plugin_drift_e2e.py``.
"""
from __future__ import annotations

import importlib.metadata as md
import json
import os
import sys
from pathlib import Path
from typing import Tuple

import pytest

# Skip the entire module if FastAPI / TestClient isn't available
# (it's in core deps, but defensive).
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    """A TestClient bound to a fresh app instance — auth defaults
    disabled (DDOC_API_KEY unset)."""
    # Make sure no leftover auth from a previous test polluted env.
    os.environ.pop("DDOC_API_KEY", None)
    from ddoc.server.app import create_app
    app = create_app(bind_info="testclient:0")
    return TestClient(app)


def _plugin_installed(name: str) -> bool:
    try:
        eps = md.entry_points(group="ddoc")
    except Exception:
        return False
    return any(ep.name == name for ep in eps)


# ── Health / metadata ────────────────────────────────────────────────


def test_root(client: TestClient):
    """``GET /`` serves the Round-15 GUI when static assets are
    packaged; the JSON metadata previously served at ``/`` now lives
    only at ``/healthz``."""
    r = client.get("/")
    assert r.status_code == 200
    # Round 15 — static assets ship with the wheel, so / returns HTML.
    assert "text/html" in r.headers["content-type"]
    assert "<title>ddoc" in r.text and "data doctor" in r.text


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert isinstance(body["plugin_count"], int)


def test_version(client: TestClient):
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert "ddoc" in body
    assert "hookspec" in body


# ── Commands introspection ──────────────────────────────────────────


def test_commands_introspection(client: TestClient):
    r = client.get("/commands")
    assert r.status_code == 200
    body = r.json()
    assert "tree" in body
    sub = body["tree"]["subcommands"]
    # Round 14 — these should always be present.
    for required in ("analyze", "examples", "fetch", "report", "export", "plugin"):
        assert required in sub, f"missing top-level subcommand: {required}"


# ── Plugin discovery ────────────────────────────────────────────────


def test_plugins_list(client: TestClient):
    r = client.get("/plugins")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert isinstance(body["plugins"], list)


def test_plugins_detectors(client: TestClient):
    r = client.get("/plugins/detectors")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # If any detector-aware plugin is installed, registry should be populated.
    if body["count"] > 0:
        for d in body["registry"]:
            assert "modality" in d
            assert "supported" in d


# ── Examples scenarios ──────────────────────────────────────────────


def test_examples_scenarios(client: TestClient):
    r = client.get("/examples/scenarios")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "timeseries" in body["modalities"]


def test_examples_generate_e2e(client: TestClient, tmp_path: Path):
    if not _plugin_installed("ddoc_timeseries"):
        pytest.skip("ddoc-plugin-timeseries not installed")
    out = tmp_path / "ts_demo"
    r = client.post(
        "/examples/generate",
        json={"modality": "timeseries", "out": str(out), "scenario": "shifted"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert (out / "ref" / "toy_ts" / "data.csv").exists()
    assert (out / "cur" / "toy_ts" / "data.csv").exists()


# ── Analyze drift (path mode) ───────────────────────────────────────


def _build_ts_pair(tmp_path: Path) -> Tuple[Path, Path]:
    sys.path.insert(0, str(Path(__file__).parent))
    from fixtures.factories import make_pair_timeseries  # type: ignore[import-not-found]
    return make_pair_timeseries(tmp_path, scenario="shifted")


def test_analyze_drift_path_mode(client: TestClient, tmp_path: Path):
    if not _plugin_installed("ddoc_timeseries"):
        pytest.skip("ddoc-plugin-timeseries not installed")
    ref, cur = _build_ts_pair(tmp_path)
    r = client.post(
        "/analyze/drift",
        json={
            "data_path_ref": str(ref),
            "data_path_cur": str(cur),
            "quiet": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("modality") == "timeseries"
    assert body.get("overall_score", 0) > 0


def test_analyze_drift_unsupported_detector(client: TestClient, tmp_path: Path):
    if not _plugin_installed("ddoc_timeseries"):
        pytest.skip("ddoc-plugin-timeseries not installed")
    ref, cur = _build_ts_pair(tmp_path)
    r = client.post(
        "/analyze/drift",
        json={
            "data_path_ref": str(ref),
            "data_path_cur": str(cur),
            "detector": "totally_unknown",
            "quiet": True,
        },
    )
    # The CLI's pre-fork registry validation rejects this → exit 2 →
    # runner returns RunError → app maps to 400 unsupported_detector.
    assert r.status_code == 400, r.text


# ── SSE stream ──────────────────────────────────────────────────────


def test_analyze_drift_stream_progress(client: TestClient, tmp_path: Path):
    if not _plugin_installed("ddoc_timeseries"):
        pytest.skip("ddoc-plugin-timeseries not installed")
    ref, cur = _build_ts_pair(tmp_path)
    payload = {
        "data_path_ref": str(ref),
        "data_path_cur": str(cur),
        "quiet": True,
    }
    with client.stream("POST", "/analyze/drift/stream", json=payload) as response:
        assert response.status_code == 200
        events: list[tuple[str, dict]] = []
        current_event = None
        for raw_line in response.iter_lines():
            line = raw_line if isinstance(raw_line, str) else raw_line.decode("utf-8")
            if not line:
                continue
            if line.startswith("event: "):
                current_event = line[len("event: "):].strip()
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
                events.append((current_event or "message", data))

    progress_events = [e for e in events if e[0] == "progress"]
    result_events = [e for e in events if e[0] == "result"]
    assert len(progress_events) >= 2, f"expected progress events, got {events}"
    assert len(result_events) == 1, f"expected one result event, got {events}"
    final = result_events[0][1]
    assert final.get("modality") == "timeseries"


# ── Fetch + report + export ─────────────────────────────────────────


def test_fetch_bare_path(client: TestClient, tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "marker.txt").write_text("hello")
    dest = tmp_path / "dest"
    r = client.post(
        "/fetch",
        json={"source_uri": str(src), "dest": str(dest)},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert (dest / "src" / "marker.txt").exists()


def test_fetch_unknown_scheme(client: TestClient, tmp_path: Path):
    r = client.post(
        "/fetch",
        json={"source_uri": "s3://bucket/missing", "dest": str(tmp_path / "x")},
    )
    # No s3 plugin → built-in fallback fails → 400.
    assert r.status_code == 400, r.text
    body = r.json()
    assert body.get("error_code") == "no_adapter_for_scheme"


def test_report_render_html(client: TestClient, tmp_path: Path):
    if not _plugin_installed("ddoc_timeseries"):
        pytest.skip("ddoc-plugin-timeseries not installed")
    ref, cur = _build_ts_pair(tmp_path)
    drift_envelope = client.post(
        "/analyze/drift",
        json={"data_path_ref": str(ref), "data_path_cur": str(cur), "quiet": True},
    ).json()
    drift_path = tmp_path / "drift.json"
    drift_path.write_text(json.dumps(drift_envelope))
    out = tmp_path / "r.html"
    r = client.post(
        "/report/render",
        json={"input": str(drift_path), "out": str(out), "format": "html"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert out.exists() and out.stat().st_size > 0


def test_export_drift_report_to_file(client: TestClient, tmp_path: Path):
    if not _plugin_installed("ddoc_timeseries"):
        pytest.skip("ddoc-plugin-timeseries not installed")
    ref, cur = _build_ts_pair(tmp_path)
    drift_envelope = client.post(
        "/analyze/drift",
        json={"data_path_ref": str(ref), "data_path_cur": str(cur), "quiet": True},
    ).json()
    drift_path = tmp_path / "drift.json"
    drift_path.write_text(json.dumps(drift_envelope))
    out_dir = tmp_path / "exports"
    r = client.post(
        "/export/drift-report",
        json={
            "input": str(drift_path),
            "target": "file",
            "config": {"out_dir": str(out_dir), "model_name": "round14-test"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert any(out_dir.iterdir())


# ── Auth toggle ─────────────────────────────────────────────────────


def test_auth_required_when_env_set(monkeypatch):
    """When DDOC_API_KEY is set, requests without the header are
    rejected and requests with the matching header pass."""
    monkeypatch.setenv("DDOC_API_KEY", "round14-secret")
    from ddoc.server.app import create_app
    app = create_app(bind_info="testclient:0")
    client = TestClient(app)

    # /healthz bypasses auth (monitoring path).
    r_health = client.get("/healthz")
    assert r_health.status_code == 200
    assert r_health.json()["auth_enabled"] is True

    # /plugins requires auth.
    r_no = client.get("/plugins")
    assert r_no.status_code == 401
    assert r_no.json()["detail"]["error_code"] == "missing_or_bad_api_key"

    r_ok = client.get("/plugins", headers={"X-API-Key": "round14-secret"})
    assert r_ok.status_code == 200
