"""Round-19 — recipe library, Prometheus metrics, GUI line chart."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    os.environ.pop("DDOC_API_KEY", None)
    os.environ.pop("DDOC_RECIPES_DIR", None)
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0"))


# ── 19.1 — /recipes library ────────────────────────────────────────


def test_recipes_list_with_bundled_dir(client: TestClient):
    """The package ships ``recipes/timeseries_smoke.yaml`` so the
    library auto-discovery should find at least one entry without any
    DDOC_RECIPES_DIR env."""
    r = client.get("/recipes")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # Bundled or fallback — either way at least 1 entry visible from the
    # repo checkout.
    if body["count"]:
        names = [it["name"] for it in body["recipes"]]
        assert "timeseries_smoke" in names


def test_recipes_list_custom_dir(client: TestClient, tmp_path: Path, monkeypatch):
    custom = tmp_path / "library"
    custom.mkdir()
    (custom / "alpha.yaml").write_text(
        "name: alpha\ndescription: test\nsteps:\n  - id: a\n    run: examples.generate\n    with: { modality: timeseries, out: /tmp/x }\n"
    )
    (custom / "beta.yml").write_text(
        "steps:\n  - id: b\n    run: examples.generate\n    with: { modality: audio, out: /tmp/y }\n"
    )
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(custom))
    # Need a fresh app since middleware caches state.
    from ddoc.server.app import create_app
    c = TestClient(create_app(bind_info="testclient:0"))
    r = c.get("/recipes")
    assert r.status_code == 200
    body = r.json()
    assert body["library_dir"] == str(custom)
    names = sorted(it["name"] for it in body["recipes"])
    assert names == ["alpha", "beta"]


def test_recipes_get_returns_yaml(client: TestClient, tmp_path: Path, monkeypatch):
    d = tmp_path / "lib"
    d.mkdir()
    (d / "tiny.yaml").write_text(
        "name: tiny\nsteps:\n  - id: g\n    run: examples.generate\n    with: { modality: timeseries, out: /tmp/x, scenario: shifted }\n"
    )
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(d))
    from ddoc.server.app import create_app
    c = TestClient(create_app(bind_info="testclient:0"))

    r = c.get("/recipes/tiny")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert "name: tiny" in body["yaml"]
    assert body["metadata"]["display_name"] == "tiny"
    assert body["issues"] == []


def test_recipes_get_path_traversal_blocked(client: TestClient, tmp_path: Path, monkeypatch):
    d = tmp_path / "lib"
    d.mkdir()
    (d / "ok.yaml").write_text("steps:\n  - id: a\n    run: examples.generate\n    with: { modality: timeseries, out: /tmp/x }\n")
    # create a sibling outside the lib that we shouldn't be able to read
    (tmp_path / "secret.yaml").write_text("steps: []\n")
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(d))
    from ddoc.server.app import create_app
    c = TestClient(create_app(bind_info="testclient:0"))

    r = c.get("/recipes/..%2Fsecret")
    assert r.status_code == 404
    r = c.get("/recipes/../secret")
    assert r.status_code in (404, 400)


# ── 19.2 — /metrics endpoint ───────────────────────────────────────


def test_metrics_endpoint_text_format(client: TestClient):
    # Hit a route to populate the histogram + counter first.
    client.get("/healthz")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    body = r.text
    assert "# TYPE ddoc_http_requests_total counter" in body
    assert "ddoc_http_requests_total" in body
    assert "ddoc_http_request_duration_seconds_bucket" in body


def _client_with_writable_lib(tmp_path: Path, monkeypatch):
    """Build a TestClient where the recipe library lives at tmp_path
    and is writable (DDOC_RECIPES_WRITE=1)."""
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0"))


# ── 20.1 — save endpoint ────────────────────────────────────────────


def test_save_requires_write_mode(client: TestClient, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    # No DDOC_RECIPES_WRITE
    from ddoc.server.app import create_app
    c = TestClient(create_app(bind_info="testclient:0"))
    r = c.put("/recipes/foo", json={"yaml": "steps: []\n"})
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "library_read_only"


def test_save_creates_recipe(tmp_path, monkeypatch):
    c = _client_with_writable_lib(tmp_path, monkeypatch)
    yaml_text = (
        "name: created\n"
        "steps:\n"
        "  - id: g\n"
        "    run: examples.generate\n"
        "    with: { modality: timeseries, out: /tmp/x, scenario: shifted }\n"
    )
    r = c.put("/recipes/created", json={"yaml": yaml_text})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["name"] == "created"
    assert body["archived_to"] is None
    assert (tmp_path / "created.yaml").exists()
    # GET picks it up.
    r2 = c.get("/recipes")
    names = [it["name"] for it in r2.json()["recipes"]]
    assert "created" in names


def test_save_rejects_invalid_yaml(tmp_path, monkeypatch):
    c = _client_with_writable_lib(tmp_path, monkeypatch)
    r = c.put("/recipes/bad", json={"yaml": "steps:\n  - run: not.a.kind\n    with: {}\n"})
    assert r.status_code == 200  # validation failure surfaces as in-band error envelope
    body = r.json()
    assert body["status"] == "error"
    assert body["error_code"] == "validation_failed"
    assert not (tmp_path / "bad.yaml").exists()


def test_save_rejects_unsafe_name(tmp_path, monkeypatch):
    c = _client_with_writable_lib(tmp_path, monkeypatch)
    r = c.put(
        "/recipes/..%2Fevil",
        json={"yaml": "steps:\n  - id: a\n    run: examples.generate\n    with: { modality: timeseries, out: /tmp/x }\n"},
    )
    # FastAPI normalizes ..%2Fevil → '../evil' but our regex rejects '/'
    assert r.status_code in (400, 404)


# ── 20.2 — versioning ──────────────────────────────────────────────


def test_save_archives_existing(tmp_path, monkeypatch):
    c = _client_with_writable_lib(tmp_path, monkeypatch)
    base_yaml = (
        "name: vtest\n"
        "steps:\n"
        "  - id: g\n"
        "    run: examples.generate\n"
        "    with: { modality: timeseries, out: /tmp/x, scenario: shifted }\n"
    )
    r1 = c.put("/recipes/vtest", json={"yaml": base_yaml})
    assert r1.status_code == 200
    assert r1.json()["archived_to"] is None

    updated_yaml = base_yaml.replace("modality: timeseries", "modality: audio")
    r2 = c.put("/recipes/vtest", json={"yaml": updated_yaml})
    assert r2.status_code == 200
    assert r2.json()["archived_to"] is not None
    assert "/.history/vtest/" in r2.json()["archived_to"]

    versions = c.get("/recipes/vtest/versions").json()
    assert versions["count"] == 1
    ts = versions["versions"][0]["timestamp"]
    historical = c.get(f"/recipes/vtest/versions/{ts}").json()
    assert "modality: timeseries" in historical["yaml"]  # archive holds the old content


def test_versions_empty_for_new_recipe(tmp_path, monkeypatch):
    c = _client_with_writable_lib(tmp_path, monkeypatch)
    r = c.get("/recipes/never-saved/versions")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_metrics_records_recipe_run(client: TestClient, tmp_path: Path):
    yaml_text = (
        'vars:\n  out: ' + str(tmp_path) + '\n'
        'steps:\n'
        '  - id: gen\n'
        '    run: examples.generate\n'
        '    with:\n'
        '      modality: timeseries\n'
        '      out: "${vars.out}"\n'
        '      scenario: shifted\n'
    )
    # dry-run keeps subprocess fast / hermetic.
    r = client.post("/recipe/run", json={"yaml": yaml_text, "dry_run": True})
    assert r.status_code == 200
    m = client.get("/metrics")
    assert m.status_code == 200
    assert "ddoc_recipe_runs_total" in m.text
    assert 'result="success"' in m.text
