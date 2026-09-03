"""Round-23 — git-backed audit trail."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git binary not available"
)


_BASE_YAML = (
    "name: gx\n"
    "steps:\n"
    "  - id: g\n"
    "    run: examples.generate\n"
    "    with: { modality: timeseries, out: /tmp/x, scenario: shifted }\n"
)


@pytest.fixture
def git_lib(tmp_path: Path, monkeypatch):
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    monkeypatch.setenv("DDOC_RECIPES_GIT", "1")
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0")), tmp_path


@pytest.fixture
def plain_lib(tmp_path: Path, monkeypatch):
    """Identical to git_lib but with DDOC_RECIPES_GIT unset."""
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    monkeypatch.delenv("DDOC_RECIPES_GIT", raising=False)
    from ddoc.server.app import create_app
    return TestClient(create_app(bind_info="testclient:0")), tmp_path


def test_save_creates_repo_and_commit(git_lib):
    c, tmp = git_lib
    r = c.put("/recipes/gx", json={"yaml": _BASE_YAML})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["git_commit"] is not None
    assert len(body["git_commit"]) == 40  # full sha
    assert (tmp / ".git").exists()


def test_listing_advertises_git_enabled(git_lib):
    c, _ = git_lib
    c.put("/recipes/gx", json={"yaml": _BASE_YAML})
    body = c.get("/recipes").json()
    assert body["git_enabled"] is True


def test_listing_git_off_by_default(plain_lib):
    c, _ = plain_lib
    c.put("/recipes/gx", json={"yaml": _BASE_YAML})
    body = c.get("/recipes").json()
    assert body["git_enabled"] is False


def test_save_returns_no_commit_when_git_disabled(plain_lib):
    c, _ = plain_lib
    r = c.put("/recipes/gx", json={"yaml": _BASE_YAML})
    assert r.status_code == 200
    assert r.json()["git_commit"] is None


def test_git_log_endpoint_lists_commits(git_lib):
    c, tmp = git_lib
    c.put("/recipes/gx", json={"yaml": _BASE_YAML})
    c.put("/recipes/gx", json={"yaml": _BASE_YAML.replace("timeseries", "audio")})
    c.delete("/recipes/gx")

    r = c.get("/git-log")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["git_enabled"] is True
    assert body["count"] >= 3
    subjects = [c["subject"] for c in body["commits"]]
    # Most recent first.
    assert subjects[0].startswith("delete gx")
    assert any(s.startswith("save gx (update)") for s in subjects)
    assert any(s.startswith("save gx (create)") for s in subjects)
    # Each entry has the four expected fields.
    for entry in body["commits"]:
        assert {"commit", "author", "date", "subject"} <= set(entry)
        assert len(entry["commit"]) == 40


def test_git_log_empty_when_disabled(plain_lib):
    c, _ = plain_lib
    c.put("/recipes/gx", json={"yaml": _BASE_YAML})
    body = c.get("/git-log").json()
    assert body["git_enabled"] is False
    assert body["count"] == 0
    assert body["commits"] == []


def test_restore_creates_commit(git_lib):
    c, _ = git_lib
    c.put("/recipes/gx", json={"yaml": _BASE_YAML})
    c.put("/recipes/gx", json={"yaml": _BASE_YAML.replace("timeseries", "audio")})
    ts = c.get("/recipes/gx/versions").json()["versions"][0]["timestamp"]
    r = c.post(f"/recipes/gx/restore/{ts}")
    assert r.status_code == 200
    assert r.json()["git_commit"] is not None
    # Verify the commit message via the log endpoint.
    log = c.get("/git-log").json()
    assert log["commits"][0]["subject"].startswith(f"restore gx@{ts}")


def test_git_failure_does_not_break_save(tmp_path, monkeypatch):
    """If git ops fail (e.g. corrupt repo) the API request still
    succeeds — git is best-effort, not load-bearing."""
    os.environ.pop("DDOC_API_KEY", None)
    monkeypatch.setenv("DDOC_RECIPES_DIR", str(tmp_path))
    monkeypatch.setenv("DDOC_RECIPES_WRITE", "1")
    monkeypatch.setenv("DDOC_RECIPES_GIT", "1")
    # Pre-create a busted .git so init/commit fails.
    (tmp_path / ".git").write_text("not a git directory")
    from ddoc.server.app import create_app
    c = TestClient(create_app(bind_info="testclient:0"))
    r = c.put("/recipes/gx", json={"yaml": _BASE_YAML})
    assert r.status_code == 200, r.text
    body = r.json()
    # File on disk still saved; git_commit is None because git failed.
    assert (tmp_path / "gx.yaml").exists()
    assert body["git_commit"] is None
