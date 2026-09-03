"""Round-24 — write-token rotation / revocation API."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


_BASE_YAML = (
    "name: tk\n"
    "steps:\n"
    "  - id: g\n"
    "    run: examples.generate\n"
    "    with: { modality: timeseries, out: /tmp/x, scenario: shifted }\n"
)


@pytest.fixture
def admin_lib(tmp_path: Path, monkeypatch):
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    monkeypatch.setenv("DDOC_RECIPES_ADMIN_TOKEN", "admin-secret")
    monkeypatch.delenv("DDOC_RECIPES_WRITE_TOKEN", raising=False)
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0")), tmp_path


@pytest.fixture
def admin_lib_with_env_token(tmp_path: Path, monkeypatch):
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    monkeypatch.setenv("DDOC_RECIPES_ADMIN_TOKEN", "admin-secret")
    monkeypatch.setenv("DDOC_RECIPES_WRITE_TOKEN", "env-secret")
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0")), tmp_path


# ── 24.1 / 24.2 — admin gate ────────────────────────────────────────


def test_admin_disabled_when_env_unset(tmp_path, monkeypatch):
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    monkeypatch.delenv("DDOC_RECIPES_ADMIN_TOKEN", raising=False)
    from ddoc.server.app import create_app
    c = TestClient(create_app(bind_info="testclient:0"))
    r = c.get("/tokens")
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "admin_disabled"


def test_admin_token_required_for_list(admin_lib):
    c, _ = admin_lib
    r = c.get("/tokens")
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_admin_token"


def test_admin_token_accepted_for_list(admin_lib):
    c, _ = admin_lib
    r = c.get("/tokens", headers={"X-Recipes-Admin-Token": "admin-secret"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["count"] == 0
    assert body["tokens"] == []


# ── 24.2 — token mint + reveal-once ─────────────────────────────────


def test_create_returns_secret_once(admin_lib):
    c, _ = admin_lib
    headers = {"X-Recipes-Admin-Token": "admin-secret"}
    r = c.post("/tokens", json={"name": "ci"}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["name"] == "ci"
    assert body["scope"] == "write"
    assert body["id"].startswith("tok_")
    assert isinstance(body["secret"], str) and len(body["secret"]) >= 16

    # The list view *never* contains the secret, only metadata.
    listed = c.get("/tokens", headers=headers).json()
    assert listed["count"] == 1
    assert "secret" not in listed["tokens"][0]
    assert "secret_hash" not in listed["tokens"][0]
    assert listed["tokens"][0]["id"] == body["id"]


def test_create_rejects_invalid_name(admin_lib):
    c, _ = admin_lib
    r = c.post("/tokens", json={"name": "bad/name!"},
               headers={"X-Recipes-Admin-Token": "admin-secret"})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_token_name"


def test_create_rejects_invalid_scope(admin_lib):
    c, _ = admin_lib
    r = c.post("/tokens", json={"name": "ci", "scope": "root"},
               headers={"X-Recipes-Admin-Token": "admin-secret"})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_token_scope"


# ── 24.3 — write endpoint accepts store credential ──────────────────


def test_write_accepted_with_store_token(admin_lib):
    c, _ = admin_lib
    admin_h = {"X-Recipes-Admin-Token": "admin-secret"}
    minted = c.post("/tokens", json={"name": "ci"}, headers=admin_h).json()
    secret = minted["secret"]

    # Without the token, write fails (token store has at least one
    # active row → write becomes gated even though no env secret).
    r = c.put("/recipes/tk", json={"yaml": _BASE_YAML})
    assert r.status_code == 401

    # With the token, write succeeds.
    r = c.put("/recipes/tk", json={"yaml": _BASE_YAML},
              headers={"X-Recipes-Write-Token": secret})
    assert r.status_code == 200, r.text


def test_revoked_token_rejected(admin_lib):
    c, _ = admin_lib
    admin_h = {"X-Recipes-Admin-Token": "admin-secret"}
    minted = c.post("/tokens", json={"name": "ci"}, headers=admin_h).json()
    secret = minted["secret"]
    tok_id = minted["id"]

    # Pre-revocation: works.
    assert c.put("/recipes/tk", json={"yaml": _BASE_YAML},
                 headers={"X-Recipes-Write-Token": secret}).status_code == 200

    # Revoke.
    rev = c.delete(f"/tokens/{tok_id}", headers=admin_h)
    assert rev.status_code == 200
    assert rev.json()["token"]["revoked_at"] is not None

    # Post-revocation: 401.
    r = c.put("/recipes/tk", json={"yaml": _BASE_YAML},
              headers={"X-Recipes-Write-Token": secret})
    assert r.status_code == 401


def test_listing_advertises_token_required_when_store_has_active(admin_lib):
    c, _ = admin_lib
    admin_h = {"X-Recipes-Admin-Token": "admin-secret"}
    body0 = c.get("/recipes").json()
    assert body0["write_token_required"] is False  # no env, no store
    c.post("/tokens", json={"name": "ci"}, headers=admin_h)
    body1 = c.get("/recipes").json()
    assert body1["write_token_required"] is True


def test_env_and_store_coexist(admin_lib_with_env_token):
    c, _ = admin_lib_with_env_token
    admin_h = {"X-Recipes-Admin-Token": "admin-secret"}
    minted = c.post("/tokens", json={"name": "rotated"}, headers=admin_h).json()

    # Both env-secret and store-secret are accepted for writes.
    r = c.put("/recipes/tk1", json={"yaml": _BASE_YAML},
              headers={"X-Recipes-Write-Token": "env-secret"})
    assert r.status_code == 200, r.text
    r = c.put("/recipes/tk2", json={"yaml": _BASE_YAML},
              headers={"X-Recipes-Write-Token": minted["secret"]})
    assert r.status_code == 200, r.text


def test_revoke_404_unknown(admin_lib):
    c, _ = admin_lib
    r = c.delete("/tokens/tok_deadbeef",
                 headers={"X-Recipes-Admin-Token": "admin-secret"})
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "token_not_found"


def test_revoke_400_bad_id_format(admin_lib):
    c, _ = admin_lib
    r = c.delete("/tokens/not-an-id",
                 headers={"X-Recipes-Admin-Token": "admin-secret"})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_token_id"


def test_token_store_is_secret_hash_only(admin_lib):
    """The .tokens.json file must never contain plaintext secrets."""
    c, tmp = admin_lib
    minted = c.post("/tokens", json={"name": "x"},
                    headers={"X-Recipes-Admin-Token": "admin-secret"}).json()
    raw = (tmp / ".tokens.json").read_text()
    assert minted["secret"] not in raw
    assert "secret_hash" in raw
