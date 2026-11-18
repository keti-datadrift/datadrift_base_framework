"""Round-21 — recipe library DELETE / restore / diff."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


_BASE_YAML = (
    "name: rt\n"
    "steps:\n"
    "  - id: g\n"
    "    run: examples.generate\n"
    "    with: { modality: timeseries, out: /tmp/x, scenario: shifted }\n"
)
_UPDATED_YAML = _BASE_YAML.replace("modality: timeseries", "modality: audio")


@pytest.fixture
def writable_lib(tmp_path: Path, monkeypatch):
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0")), tmp_path


@pytest.fixture
def readonly_lib(tmp_path: Path, monkeypatch):
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.delenv("DDOC_RECIPES_WRITE", raising=False)
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0")), tmp_path


# ── 21.1 — DELETE ──────────────────────────────────────────────────


def test_delete_archives_then_removes(writable_lib):
    c, tmp = writable_lib
    r = c.put("/recipes/rt", json={"yaml": _BASE_YAML})
    assert r.status_code == 200, r.text
    assert (tmp / "rt.yaml").exists()

    r = c.delete("/recipes/rt")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["archived_to"] is not None
    assert "/.history/rt/" in body["archived_to"]
    assert not (tmp / "rt.yaml").exists()
    # archive contains the deleted content
    assert Path(body["archived_to"]).read_text() == _BASE_YAML


def test_delete_requires_write_mode(readonly_lib):
    c, _ = readonly_lib
    r = c.delete("/recipes/whatever")
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "library_read_only"


def test_delete_404_on_missing(writable_lib):
    c, _ = writable_lib
    r = c.delete("/recipes/never-existed")
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "recipe_not_found"


# ── 21.2 — restore ──────────────────────────────────────────────────


def test_restore_brings_back_old_content(writable_lib):
    c, tmp = writable_lib
    # Two saves so we have a snapshot of base + the updated content live.
    c.put("/recipes/rt", json={"yaml": _BASE_YAML})
    r2 = c.put("/recipes/rt", json={"yaml": _UPDATED_YAML})
    snapshot_ts = c.get("/recipes/rt/versions").json()["versions"][0]["timestamp"]

    r = c.post(f"/recipes/rt/restore/{snapshot_ts}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["archived_to"] is not None  # the audio content was archived
    # active file now matches the original base again
    assert (tmp / "rt.yaml").read_text() == _BASE_YAML
    # And the audio variant is recoverable as a brand-new snapshot
    versions = c.get("/recipes/rt/versions").json()["versions"]
    assert versions[0]["timestamp"] != snapshot_ts


def test_restore_404_unknown_ts(writable_lib):
    c, _ = writable_lib
    c.put("/recipes/rt", json={"yaml": _BASE_YAML})
    r = c.post("/recipes/rt/restore/19990101T000000Z")
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "version_not_found"


def test_restore_requires_write_mode(readonly_lib):
    c, _ = readonly_lib
    r = c.post("/recipes/rt/restore/19990101T000000Z")
    assert r.status_code == 403


# ── 21.3 — diff ─────────────────────────────────────────────────────


def test_diff_head_vs_latest_snapshot_default(writable_lib):
    c, _ = writable_lib
    c.put("/recipes/rt", json={"yaml": _BASE_YAML})
    c.put("/recipes/rt", json={"yaml": _UPDATED_YAML})

    r = c.get("/recipes/rt/diff")  # defaults: from=HEAD, to=latest snapshot
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["from"] == "HEAD"
    assert body["to"] is not None
    assert body["identical"] is False
    # HEAD = audio; snapshot = timeseries → diff line removes audio, adds timeseries
    assert "modality: audio" in body["diff"]
    assert "modality: timeseries" in body["diff"]


def test_diff_explicit_refs(writable_lib):
    c, _ = writable_lib
    c.put("/recipes/rt", json={"yaml": _BASE_YAML})
    c.put("/recipes/rt", json={"yaml": _UPDATED_YAML})
    versions = c.get("/recipes/rt/versions").json()["versions"]
    ts = versions[0]["timestamp"]

    r = c.get(f"/recipes/rt/diff?from={ts}&to=HEAD")
    assert r.status_code == 200
    body = r.json()
    assert body["from"] == ts
    assert body["to"] == "HEAD"
    assert "+++" in body["diff"]
    assert body["identical"] is False


def test_diff_no_snapshots_yet(writable_lib):
    c, _ = writable_lib
    c.put("/recipes/rt", json={"yaml": _BASE_YAML})
    r = c.get("/recipes/rt/diff")
    assert r.status_code == 200
    body = r.json()
    assert body["diff"] == ""
    assert body.get("note") == "no snapshots yet"


def test_diff_404_on_unknown_ref(writable_lib):
    c, _ = writable_lib
    c.put("/recipes/rt", json={"yaml": _BASE_YAML})
    r = c.get("/recipes/rt/diff?from=HEAD&to=19990101T000000Z")
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "version_not_found"


def test_diff_identical_when_same_ref(writable_lib):
    c, _ = writable_lib
    c.put("/recipes/rt", json={"yaml": _BASE_YAML})
    r = c.get("/recipes/rt/diff?from=HEAD&to=HEAD")
    assert r.status_code == 200
    assert r.json()["identical"] is True
