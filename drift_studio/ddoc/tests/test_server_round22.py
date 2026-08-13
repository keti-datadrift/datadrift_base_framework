"""Round-22 — recipe-library write-token gating + library exposure
of `write_token_required`."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


_BASE_YAML = (
    "name: tt\n"
    "steps:\n"
    "  - id: g\n"
    "    run: examples.generate\n"
    "    with: { modality: timeseries, out: /tmp/x, scenario: shifted }\n"
)


@pytest.fixture
def token_lib(tmp_path: Path, monkeypatch):
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    monkeypatch.setenv("DDOC_RECIPES_WRITE_TOKEN", "s3cr3t")
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0")), tmp_path


def test_listing_advertises_write_token_required(token_lib):
    c, _ = token_lib
    body = c.get("/recipes").json()
    assert body["write_enabled"] is True
    assert body["write_token_required"] is True


def test_save_without_token_rejected(token_lib):
    c, tmp = token_lib
    r = c.put("/recipes/tt", json={"yaml": _BASE_YAML})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_write_token"
    assert not (tmp / "tt.yaml").exists()


def test_save_with_wrong_token_rejected(token_lib):
    c, _ = token_lib
    r = c.put(
        "/recipes/tt",
        json={"yaml": _BASE_YAML},
        headers={"X-Recipes-Write-Token": "wrong"},
    )
    assert r.status_code == 401


def test_save_with_correct_token_accepted(token_lib):
    c, tmp = token_lib
    r = c.put(
        "/recipes/tt",
        json={"yaml": _BASE_YAML},
        headers={"X-Recipes-Write-Token": "s3cr3t"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"
    assert (tmp / "tt.yaml").exists()


def test_delete_and_restore_also_token_gated(token_lib):
    c, _ = token_lib
    headers = {"X-Recipes-Write-Token": "s3cr3t"}
    # seed
    c.put("/recipes/tt", json={"yaml": _BASE_YAML}, headers=headers)
    c.put("/recipes/tt", json={"yaml": _BASE_YAML.replace("timeseries", "audio")},
          headers=headers)
    ts = c.get("/recipes/tt/versions").json()["versions"][0]["timestamp"]

    # restore without token
    r = c.post(f"/recipes/tt/restore/{ts}")
    assert r.status_code == 401
    # delete without token
    r = c.delete("/recipes/tt")
    assert r.status_code == 401

    # both succeed with token
    r = c.post(f"/recipes/tt/restore/{ts}", headers=headers)
    assert r.status_code == 200
    r = c.delete("/recipes/tt", headers=headers)
    assert r.status_code == 200


def test_read_endpoints_anonymous_even_with_token(token_lib):
    """Token gating only affects writes — listing / get / versions /
    diff stay open under DDOC_RECIPES_WRITE_TOKEN alone."""
    c, _ = token_lib
    headers = {"X-Recipes-Write-Token": "s3cr3t"}
    c.put("/recipes/tt", json={"yaml": _BASE_YAML}, headers=headers)
    # All anonymous reads succeed.
    assert c.get("/recipes").status_code == 200
    assert c.get("/recipes/tt").status_code == 200
    assert c.get("/recipes/tt/versions").status_code == 200
    assert c.get("/recipes/tt/diff").status_code == 200


def test_listing_shows_token_not_required_when_unset(tmp_path, monkeypatch):
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    monkeypatch.delenv("DDOC_RECIPES_WRITE_TOKEN", raising=False)
    from ddoc.server.app import create_app
    c = TestClient(create_app(bind_info="testclient:0"))
    body = c.get("/recipes").json()
    assert body["write_enabled"] is True
    assert body["write_token_required"] is False
    # Plain PUT works — no token required.
    r = c.put("/recipes/tt", json={"yaml": _BASE_YAML})
    assert r.status_code == 200
