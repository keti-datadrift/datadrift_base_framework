"""Round-17 — REST endpoints for the recipe layer."""
from __future__ import annotations

import importlib.metadata as md
import json
import os
import textwrap
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


def _plugin_installed(name: str) -> bool:
    try:
        return any(ep.name == name for ep in md.entry_points(group="ddoc"))
    except Exception:
        return False


@pytest.fixture
def client():
    os.environ.pop("DDOC_API_KEY", None)
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0"))


# ── /recipe/validate ────────────────────────────────────────────────


def test_validate_missing_input(client: TestClient):
    r = client.post("/recipe/validate", json={})
    assert r.status_code == 400
    assert r.json()["error_code"] == "missing_recipe_input"


def test_validate_inline_ok(client: TestClient):
    yaml_text = textwrap.dedent("""
        name: tiny
        steps:
          - id: gen
            run: examples.generate
            with:
              modality: timeseries
              out: /tmp/x
              scenario: shifted
    """)
    r = client.post("/recipe/validate", json={"yaml": yaml_text})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["step_count"] == 1


def test_validate_inline_with_issue(client: TestClient):
    yaml_text = textwrap.dedent("""
        steps:
          - id: a
            run: not.a.kind
            with: {}
    """)
    r = client.post("/recipe/validate", json={"yaml": yaml_text})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "error"
    assert any("unknown `run`" in i for i in body["issues"])


def test_validate_path_not_found(client: TestClient):
    r = client.post("/recipe/validate", json={"path": "/nonexistent/recipe.yaml"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "recipe_not_found"


# ── /recipe/run (dry-run) ───────────────────────────────────────────


def test_run_dry_run_resolves_substitution(client: TestClient):
    yaml_text = textwrap.dedent("""
        vars:
          out: /tmp/dry
        steps:
          - id: gen
            run: examples.generate
            with:
              modality: timeseries
              out: "${vars.out}"
              scenario: shifted
    """)
    r = client.post("/recipe/run", json={"yaml": yaml_text, "dry_run": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    step = body["steps"][0]
    assert step["skipped"] is True
    assert step["skipped_reason"] == "dry_run"
    assert "/tmp/dry" in " ".join(step["argv"])


# ── /recipe/run real execution ──────────────────────────────────────


@pytest.mark.skipif(
    not _plugin_installed("ddoc_timeseries"),
    reason="ddoc-plugin-timeseries not installed",
)
def test_run_e2e_inline(client: TestClient, tmp_path: Path):
    data_root = tmp_path / "data"
    workspace = tmp_path / "wsp"
    yaml_text = textwrap.dedent(f"""
        workspace: {workspace}
        steps:
          - id: gen
            run: examples.generate
            with:
              modality: timeseries
              out: {data_root}
              scenario: shifted
          - id: drift
            run: analyze.drift
            with:
              data_path_ref: {data_root}/ref
              data_path_cur: {data_root}/cur
              quiet: true
    """)
    r = client.post("/recipe/run", json={"yaml": yaml_text})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    drift_step = next(s for s in body["steps"] if s["id"] == "drift")
    assert drift_step["json"]["modality"] == "timeseries"
    assert drift_step["output"]
    assert Path(drift_step["output"]).exists()


# ── /recipe/run/stream ──────────────────────────────────────────────


@pytest.mark.skipif(
    not _plugin_installed("ddoc_timeseries"),
    reason="ddoc-plugin-timeseries not installed",
)
def test_run_stream_emits_events(client: TestClient, tmp_path: Path):
    data_root = tmp_path / "data"
    workspace = tmp_path / "wsp"
    yaml_text = textwrap.dedent(f"""
        workspace: {workspace}
        steps:
          - id: gen
            run: examples.generate
            with: {{ modality: timeseries, out: {data_root}, scenario: shifted }}
          - id: drift
            run: analyze.drift
            with:
              data_path_ref: {data_root}/ref
              data_path_cur: {data_root}/cur
              quiet: true
    """)
    with client.stream("POST", "/recipe/run/stream", json={"yaml": yaml_text}) as response:
        assert response.status_code == 200
        events: list[tuple[str, dict]] = []
        current = None
        for raw in response.iter_lines():
            line = raw if isinstance(raw, str) else raw.decode("utf-8")
            if not line:
                continue
            if line.startswith("event: "):
                current = line[7:].strip()
            elif line.startswith("data: "):
                events.append((current or "message", json.loads(line[6:])))
    progress = [e for e in events if e[0] == "progress"]
    result = [e for e in events if e[0] == "result"]
    assert len(progress) == 2
    assert len(result) == 1
    assert result[0][1]["status"] == "success"


# ── 17.3: when conditional ──────────────────────────────────────────


@pytest.mark.skipif(
    not _plugin_installed("ddoc_timeseries"),
    reason="ddoc-plugin-timeseries not installed",
)
def test_when_conditional_skips_when_false(client: TestClient, tmp_path: Path):
    data_root = tmp_path / "data"
    workspace = tmp_path / "wsp"
    # Recipe runs drift then conditionally renders a report only if
    # overall_score > 100 (which our toy never reaches → step skipped).
    yaml_text = textwrap.dedent(f"""
        workspace: {workspace}
        steps:
          - id: gen
            run: examples.generate
            with: {{ modality: timeseries, out: {data_root}, scenario: shifted }}
          - id: drift
            run: analyze.drift
            with:
              data_path_ref: {data_root}/ref
              data_path_cur: {data_root}/cur
              quiet: true
          - id: report_md
            run: report.render
            when: "${{steps.drift.json.overall_score}} > 100"
            with:
              input: "${{steps.drift.output}}"
              out: {tmp_path}/report.md
              format: md
    """)
    r = client.post("/recipe/run", json={"yaml": yaml_text})
    assert r.status_code == 200, r.text
    body = r.json()
    steps = {s["id"]: s for s in body["steps"]}
    assert steps["report_md"]["skipped"] is True
    assert steps["report_md"]["skipped_reason"] == "when"


@pytest.mark.skipif(
    not _plugin_installed("ddoc_timeseries"),
    reason="ddoc-plugin-timeseries not installed",
)
def test_when_conditional_runs_when_true(client: TestClient, tmp_path: Path):
    data_root = tmp_path / "data"
    workspace = tmp_path / "wsp"
    yaml_text = textwrap.dedent(f"""
        workspace: {workspace}
        steps:
          - id: gen
            run: examples.generate
            with: {{ modality: timeseries, out: {data_root}, scenario: shifted }}
          - id: drift
            run: analyze.drift
            with:
              data_path_ref: {data_root}/ref
              data_path_cur: {data_root}/cur
              quiet: true
          - id: report_md
            run: report.render
            when: "${{steps.drift.json.overall_score}} > 0.1"
            with:
              input: "${{steps.drift.output}}"
              out: {tmp_path}/report.md
              format: md
    """)
    r = client.post("/recipe/run", json={"yaml": yaml_text})
    assert r.status_code == 200, r.text
    body = r.json()
    steps = {s["id"]: s for s in body["steps"]}
    assert not steps["report_md"]["skipped"]
    assert (tmp_path / "report.md").exists()
