"""``/recipes`` — site-shared recipe library (Round 19 → Round 21).

The library is whatever directory ``DDOC_RECIPES_DIR`` env points to,
or ``recipes/`` next to the ddoc install. One YAML file = one recipe.

Endpoints:

* ``GET    /recipes``                       → list `{name, file, display_name, step_count}`
* ``GET    /recipes/{name}``                → YAML text + parsed metadata + validation issues
* ``PUT    /recipes/{name}``                → save / update YAML (Round 20, write-mode only)
* ``DELETE /recipes/{name}``                → soft-delete (auto-archive) (Round 21)
* ``POST   /recipes/{name}/restore/{ts}``   → restore active from a snapshot (Round 21)
* ``GET    /recipes/{name}/diff``           → unified diff between two refs (Round 21)
* ``GET    /recipes/{name}/versions``       → snapshot history under .history/ (Round 20)
* ``GET    /recipes/{name}/versions/{ts}``  → one historical YAML
* ``GET    /git-log``                       → recent commits (when DDOC_RECIPES_GIT=1) (Round 23)
* ``GET    /tokens``                        → list write tokens (admin-gated) (Round 24)
* ``POST   /tokens``                        → mint a new write token (admin-gated)
* ``DELETE /tokens/{tok_id}``               → revoke a write token (admin-gated)

Write-mode is opt-in via ``DDOC_RECIPES_WRITE=1`` env so a casual
``ddoc serve`` deployment cannot have its recipes overwritten by
unauthenticated callers (combined with ``DDOC_API_KEY`` for actual
production access control).

Versioning: every successful PUT/DELETE/restore also writes
``<library>/.history/<name>/<UTC ts>.yaml`` so the previous content is
recoverable. The active recipe stays at ``<library>/<name>.yaml``;
``versions`` listing is most-recent-first.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from ..auth import require_api_key
from .. import token_store

_log = logging.getLogger(__name__)

router = APIRouter(tags=["recipes"], dependencies=[Depends(require_api_key)])


# Allow only conservative filename characters in URL slugs so write
# routes can't traverse outside the library.
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _write_enabled() -> bool:
    return os.getenv("DDOC_RECIPES_WRITE", "").lower() in ("1", "true", "yes")


def _write_token_required() -> Optional[str]:
    """Return the configured write-token, or None if no token gating."""
    tok = os.getenv("DDOC_RECIPES_WRITE_TOKEN", "")
    return tok or None


def _write_token_active() -> bool:
    """True iff *some* write-token gate is configured — env single
    secret (Round 22) and/or the token store has been initialized
    (Round 24). Once the store exists, the gate stays on even if all
    tokens are revoked, so revoking-then-anonymous writes is
    impossible."""
    if _write_token_required() is not None:
        return True
    base = _resolve_library_dir()
    if base is None:
        return False
    return token_store.is_initialized(base.resolve())


# ── Round 23 — git-backed audit trail ───────────────────────────────


def _git_enabled() -> bool:
    """Git audit trail is opt-in via DDOC_RECIPES_GIT=1.

    When on, every successful write commits the library directory so a
    full audit history (with diffs) is queryable via ``git log`` outside
    the API. ``.history/`` archives stay as before — the two are
    complementary.
    """
    return os.getenv("DDOC_RECIPES_GIT", "").lower() in ("1", "true", "yes")


def _git_available() -> bool:
    return shutil.which("git") is not None


def _git_run(base: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git subcommand inside ``base``; never raises so the API
    request itself isn't sunk by a git failure."""
    return subprocess.run(
        ["git", "-C", str(base), *args],
        capture_output=True, text=True, timeout=15, check=False,
    )


def _git_ensure_repo(base: Path) -> bool:
    """Init a git repo at ``base`` if missing. Returns True when the
    directory is now a working repo."""
    if (base / ".git").exists():
        return True
    if not _git_available():
        return False
    init = _git_run(base, "init", "-q")
    if init.returncode != 0:
        _log.warning("git init failed in %s: %s", base, init.stderr)
        return False
    # Ensure a sane default identity for the commits we make. Don't
    # clobber existing config.
    cfg = _git_run(base, "config", "user.email")
    if not cfg.stdout.strip():
        _git_run(base, "config", "user.email", "ddoc-serve@localhost")
        _git_run(base, "config", "user.name", "ddoc-serve")
    return (base / ".git").exists()


def _git_commit_after_write(base: Path, message: str) -> Optional[str]:
    """Stage every change in the library and commit. Returns the new
    commit SHA on success, ``None`` on no-op or failure."""
    if not _git_enabled():
        return None
    if not _git_available():
        return None
    if not _git_ensure_repo(base):
        return None
    add = _git_run(base, "add", "-A")
    if add.returncode != 0:
        _log.warning("git add failed in %s: %s", base, add.stderr)
        return None
    # ``--allow-empty`` so ops that touched nothing on disk (e.g.
    # an idempotent restore to identical content) still leave a
    # marker. Some ops legitimately have nothing to commit.
    commit = _git_run(base, "commit", "-q", "--allow-empty", "-m", message)
    if commit.returncode != 0:
        _log.warning("git commit failed in %s: %s", base, commit.stderr)
        return None
    rev = _git_run(base, "rev-parse", "HEAD")
    sha = rev.stdout.strip() if rev.returncode == 0 else None
    return sha or None


def _check_write_enabled() -> None:
    if not _write_enabled():
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "error_code": "library_read_only",
                "message": "Recipe library is read-only. Set DDOC_RECIPES_WRITE=1 to enable save/versioning routes.",
            },
        )


def _check_write_token(request: Request) -> None:
    """Gate write endpoints. The check is *required* if either
    ``DDOC_RECIPES_WRITE_TOKEN`` env is set or the library's token
    store has any active tokens.

    Validation: header must equal the env secret, or its hash must
    match a non-revoked token in ``<library>/.tokens.json``. Either
    suffices — deployments can mix the env single-secret (Round 22)
    with multi-token rotation (Round 24).
    """
    env_expected = _write_token_required()
    base = _resolve_library_dir()
    store_initialized = base is not None and token_store.is_initialized(base.resolve())
    if env_expected is None and not store_initialized:
        return
    provided = request.headers.get("x-recipes-write-token", "")
    if env_expected is not None and provided == env_expected:
        return
    if base is not None and token_store.verify(base.resolve(), provided):
        return
    raise HTTPException(
        status_code=401,
        detail={
            "status": "error",
            "error_code": "invalid_write_token",
            "message": "Missing or invalid X-Recipes-Write-Token header.",
        },
    )


# ── Round 24 — admin gate (token CRUD endpoints) ────────────────────


def _admin_token_required() -> Optional[str]:
    tok = os.getenv("DDOC_RECIPES_ADMIN_TOKEN", "")
    return tok or None


def _check_admin_token(request: Request) -> None:
    """Gate token-management endpoints. ``DDOC_RECIPES_ADMIN_TOKEN``
    must be set; the request must carry a matching
    ``X-Recipes-Admin-Token`` header. Without admin token configured
    at all, the management endpoints are unreachable (closed-by-default
    so a casual ``ddoc serve`` never accidentally exposes token CRUD).
    """
    expected = _admin_token_required()
    if expected is None:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "error_code": "admin_disabled",
                "message": "Token management is disabled. Set DDOC_RECIPES_ADMIN_TOKEN to enable.",
            },
        )
    provided = request.headers.get("x-recipes-admin-token", "")
    if provided != expected:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "error_code": "invalid_admin_token",
                "message": "Missing or invalid X-Recipes-Admin-Token header.",
            },
        )


def _check_safe_name(name: str) -> None:
    if not _SAFE_NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "error_code": "invalid_recipe_name",
                "message": "name must match [A-Za-z0-9][A-Za-z0-9_.-]{0,127}",
                "name": name,
            },
        )


def _resolve_library_dir() -> Optional[Path]:
    """Return the recipe library directory, or None if not configured."""
    env_dir = os.getenv("DDOC_RECIPES_DIR")
    if env_dir:
        d = Path(env_dir)
        return d if d.exists() else None
    # Fall back to the bundled ``recipes/`` next to the package — works
    # for editable installs (monorepo dev) and for site installs that
    # symlink a curated dir there.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "recipes"
        if candidate.exists() and any(candidate.glob("*.yaml")):
            return candidate
    return None


def _safe_join(base: Path, name: str) -> Path:
    """Resolve ``name.yaml`` (or ``.yml``) under ``base`` and refuse
    anything outside the library."""
    for suffix in (".yaml", ".yml"):
        candidate = (base / f"{name}{suffix}").resolve()
        if candidate.is_file() and base.resolve() in candidate.parents:
            return candidate
    raise FileNotFoundError(name)


def _parse_recipe_meta(path: Path) -> Dict[str, Any]:
    """Extract a recipe's ``name`` / ``description`` / step count
    without running validation. Returns shape suitable for /recipes
    listing."""
    try:
        import yaml
    except ImportError:
        return {"file": path.name, "error": "yaml_missing"}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        return {"file": path.name, "error": f"parse_failed: {e}"}
    if not isinstance(data, dict):
        return {"file": path.name, "error": "top_level_not_mapping"}
    steps = data.get("steps") or []
    return {
        "name": path.stem,
        "file": path.name,
        "display_name": data.get("name"),
        "description": data.get("description"),
        "step_count": len(steps) if isinstance(steps, list) else 0,
    }


@router.get("/recipes")
def list_recipes() -> Dict[str, Any]:
    """List every YAML recipe in the configured library."""
    base = _resolve_library_dir()
    if base is None:
        return {
            "status": "ok",
            "library_dir": None,
            "count": 0,
            "recipes": [],
            "hint": (
                "Set DDOC_RECIPES_DIR env to a directory of recipe YAML files, "
                "or place them under <package_root>/recipes/."
            ),
        }
    recipes: List[Dict[str, Any]] = []
    for p in sorted(base.glob("*.yaml")) + sorted(base.glob("*.yml")):
        # Skip the .history archive — it's only reachable via
        # /recipes/{name}/versions endpoints.
        if p.is_file() and ".history" not in p.parts:
            recipes.append(_parse_recipe_meta(p))
    return {
        "status": "ok",
        "library_dir": str(base),
        "count": len(recipes),
        "write_enabled": _write_enabled(),
        "write_token_required": _write_token_active(),
        "git_enabled": _git_enabled() and (base / ".git").exists(),
        "recipes": recipes,
    }


@router.get("/recipes/{name}")
def get_recipe(name: str) -> Dict[str, Any]:
    """Return the YAML text + parsed metadata + validation issues."""
    base = _resolve_library_dir()
    if base is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "library_not_configured",
                    "message": "DDOC_RECIPES_DIR not set and no bundled recipes/ found."},
        )
    try:
        path = _safe_join(base, name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "recipe_not_found", "name": name},
        )

    yaml_text = path.read_text(encoding="utf-8")
    meta = _parse_recipe_meta(path)
    issues: List[str] = []
    try:
        from ddoc.core.recipe import Recipe
        recipe = Recipe.load(path)
        issues = recipe.validate()
    except Exception as e:  # noqa: BLE001
        issues = [f"load_failed: {e}"]
    return {
        "status": "ok",
        "name": name,
        "path": str(path),
        "yaml": yaml_text,
        "metadata": meta,
        "issues": issues,
        "write_enabled": _write_enabled(),
        "write_token_required": _write_token_active(),
        "git_enabled": _git_enabled() and (base / ".git").exists(),
    }


# ── Round 20 — write + versioning ───────────────────────────────────


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _archive_existing(base: Path, name: str) -> Optional[str]:
    """Snapshot the current active recipe to .history/<name>/<ts>.yaml
    before overwriting. Returns the archive path on success, or None
    when there's nothing to archive (new file).

    Timestamp granularity is one second; if multiple archives land in
    the same second (back-to-back saves, restore-then-save), append a
    ``-N`` suffix to keep each snapshot recoverable.
    """
    try:
        existing = _safe_join(base, name)
    except FileNotFoundError:
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    history_dir = base / ".history" / name
    history_dir.mkdir(parents=True, exist_ok=True)
    archive = history_dir / f"{ts}.yaml"
    n = 1
    while archive.exists():
        archive = history_dir / f"{ts}-{n}.yaml"
        n += 1
    archive.write_text(existing.read_text(encoding="utf-8"), encoding="utf-8")
    return str(archive)


@router.put("/recipes/{name}")
def save_recipe(
    name: str,
    request: Request,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """Save (create or update) a recipe.

    Body: ``{yaml: "..."}``. The YAML is parsed + validated before
    writing; write fails (no archive, no overwrite) if validation
    surfaces structural issues. The previous content (if any) is
    snapshotted under ``.history/<name>/<UTC ts>.yaml``.

    Requires ``DDOC_RECIPES_WRITE=1`` env. URL ``name`` must match
    a conservative slug pattern. If ``DDOC_RECIPES_WRITE_TOKEN`` is
    set, the ``X-Recipes-Write-Token`` header must match.
    """
    _check_write_enabled()
    _check_write_token(request)
    _check_safe_name(name)

    yaml_text = payload.get("yaml")
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "error_code": "missing_yaml",
                    "message": "Body must be {'yaml': <non-empty string>}."},
        )

    base = _resolve_library_dir()
    if base is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "library_not_configured",
                    "message": "DDOC_RECIPES_DIR not set and no bundled recipes/ found."},
        )
    base = base.resolve()

    # Validate via the recipe loader before writing.
    import tempfile
    from ddoc.core.recipe import Recipe, RecipeError
    tmp_path = Path(tempfile.mkstemp(prefix="ddoc-recipe-save-", suffix=".yaml")[1])
    tmp_path.write_text(yaml_text, encoding="utf-8")
    try:
        recipe = Recipe.load(tmp_path)
    except RecipeError as e:
        return {"status": "error", "error_code": e.code, "message": str(e)}
    finally:
        try:
            tmp_path.unlink()
        except Exception:  # noqa: BLE001
            pass
    issues = recipe.validate()
    if issues:
        return {"status": "error", "error_code": "validation_failed", "issues": issues}

    target = base / f"{name}.yaml"
    archive_path = _archive_existing(base, name)
    _atomic_write(target, yaml_text)
    git_sha = _git_commit_after_write(
        base,
        f"save {name} ({'create' if archive_path is None else 'update'})",
    )
    return {
        "status": "ok",
        "name": name,
        "path": str(target),
        "archived_to": archive_path,
        "step_count": len(recipe.steps),
        "git_commit": git_sha,
    }


@router.get("/recipes/{name}/versions")
def list_versions(name: str) -> Dict[str, Any]:
    """List archived snapshots of a recipe (most-recent first)."""
    _check_safe_name(name)
    base = _resolve_library_dir()
    if base is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "library_not_configured"},
        )
    history_dir = base / ".history" / name
    if not history_dir.exists():
        return {"status": "ok", "name": name, "count": 0, "versions": []}
    versions = sorted(
        (p for p in history_dir.glob("*.yaml") if p.is_file()),
        key=lambda p: p.stem,
        reverse=True,
    )
    return {
        "status": "ok",
        "name": name,
        "count": len(versions),
        "versions": [
            {"timestamp": p.stem, "size_bytes": p.stat().st_size, "file": p.name}
            for p in versions
        ],
    }


@router.get("/recipes/{name}/versions/{ts}")
def get_version(name: str, ts: str) -> Dict[str, Any]:
    """Return the YAML text of a specific historical snapshot."""
    _check_safe_name(name)
    if not _SAFE_NAME_RE.match(ts):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "error_code": "invalid_timestamp"},
        )
    base = _resolve_library_dir()
    if base is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "library_not_configured"},
        )
    candidate = (base / ".history" / name / f"{ts}.yaml").resolve()
    history_root = (base / ".history" / name).resolve()
    if history_root not in candidate.parents or not candidate.is_file():
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "version_not_found",
                    "name": name, "timestamp": ts},
        )
    return {
        "status": "ok",
        "name": name,
        "timestamp": ts,
        "yaml": candidate.read_text(encoding="utf-8"),
        "size_bytes": candidate.stat().st_size,
    }


# ── Round 21 — delete / restore / diff ──────────────────────────────


def _resolve_ref_yaml(base: Path, name: str, ref: str) -> str:
    """Resolve a ref ('HEAD' or a snapshot timestamp) to YAML text."""
    if ref == "HEAD":
        try:
            active = _safe_join(base, name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "error_code": "recipe_not_found",
                        "name": name, "ref": ref},
            )
        return active.read_text(encoding="utf-8")
    if not _SAFE_NAME_RE.match(ref):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "error_code": "invalid_ref", "ref": ref},
        )
    candidate = (base / ".history" / name / f"{ref}.yaml").resolve()
    history_root = (base / ".history" / name).resolve()
    if history_root not in candidate.parents or not candidate.is_file():
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "version_not_found",
                    "name": name, "ref": ref},
        )
    return candidate.read_text(encoding="utf-8")


@router.delete("/recipes/{name}")
def delete_recipe(name: str, request: Request) -> Dict[str, Any]:
    """Delete a recipe. The current content is archived first so a
    subsequent ``POST /recipes/{name}/restore/{ts}`` can recover it.

    Requires ``DDOC_RECIPES_WRITE=1``.
    """
    _check_write_enabled()
    _check_write_token(request)
    _check_safe_name(name)
    base = _resolve_library_dir()
    if base is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "library_not_configured"},
        )
    base = base.resolve()
    try:
        active = _safe_join(base, name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "recipe_not_found", "name": name},
        )
    archive_path = _archive_existing(base, name)
    active.unlink()
    git_sha = _git_commit_after_write(base, f"delete {name}")
    return {
        "status": "ok",
        "name": name,
        "deleted_path": str(active),
        "archived_to": archive_path,
        "git_commit": git_sha,
    }


@router.post("/recipes/{name}/restore/{ts}")
def restore_version(name: str, ts: str, request: Request) -> Dict[str, Any]:
    """Replace the active recipe with the YAML from a historical
    snapshot. The current active content is archived first so the
    restore itself is reversible.

    Requires ``DDOC_RECIPES_WRITE=1``. ``ts`` must match a file under
    ``.history/<name>/``.
    """
    _check_write_enabled()
    _check_write_token(request)
    _check_safe_name(name)
    if not _SAFE_NAME_RE.match(ts):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "error_code": "invalid_timestamp"},
        )
    base = _resolve_library_dir()
    if base is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "library_not_configured"},
        )
    base = base.resolve()

    snapshot = (base / ".history" / name / f"{ts}.yaml").resolve()
    history_root = (base / ".history" / name).resolve()
    if history_root not in snapshot.parents or not snapshot.is_file():
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "version_not_found",
                    "name": name, "timestamp": ts},
        )
    yaml_text = snapshot.read_text(encoding="utf-8")
    target = base / f"{name}.yaml"
    archive_path = _archive_existing(base, name)
    _atomic_write(target, yaml_text)
    git_sha = _git_commit_after_write(base, f"restore {name}@{ts}")
    return {
        "status": "ok",
        "name": name,
        "restored_from": str(snapshot),
        "archived_to": archive_path,
        "path": str(target),
        "git_commit": git_sha,
    }


@router.get("/recipes/{name}/diff")
def diff_recipe(
    name: str,
    from_: str = Query("HEAD", alias="from"),
    to: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Unified-diff two refs of a recipe.

    Each ref is either ``HEAD`` (current active content) or a snapshot
    timestamp under ``.history/<name>/``. Defaults: ``from=HEAD``,
    ``to=`` most-recent snapshot — convenient for "what changed since
    last save?".
    """
    _check_safe_name(name)
    base = _resolve_library_dir()
    if base is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "library_not_configured"},
        )
    base = base.resolve()

    if to is None:
        # Default: compare HEAD against the most-recent snapshot.
        history_dir = base / ".history" / name
        if not history_dir.exists():
            return {
                "status": "ok",
                "name": name,
                "from": from_,
                "to": None,
                "diff": "",
                "note": "no snapshots yet",
            }
        snaps = sorted((p for p in history_dir.glob("*.yaml") if p.is_file()),
                       key=lambda p: p.stem, reverse=True)
        if not snaps:
            return {
                "status": "ok",
                "name": name,
                "from": from_,
                "to": None,
                "diff": "",
                "note": "no snapshots yet",
            }
        to = snaps[0].stem

    a_text = _resolve_ref_yaml(base, name, from_)
    b_text = _resolve_ref_yaml(base, name, to)

    import difflib
    diff_lines = list(difflib.unified_diff(
        a_text.splitlines(keepends=True),
        b_text.splitlines(keepends=True),
        fromfile=f"{name}@{from_}",
        tofile=f"{name}@{to}",
        n=3,
    ))
    return {
        "status": "ok",
        "name": name,
        "from": from_,
        "to": to,
        "diff": "".join(diff_lines),
        "identical": not diff_lines,
    }


# ── Round 23 — git log endpoint ─────────────────────────────────────


@router.get("/git-log")
def git_log(limit: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
    """Recent commits in the library (when ``DDOC_RECIPES_GIT=1`` was
    on at the time those commits were made). Empty list when git mode
    isn't active or no commits exist yet.

    Each entry: ``{commit, author, date, subject}``. Use ``git -C
    <library_dir> show <commit>`` for the full diff (or call
    ``GET /recipes/{name}/diff`` for ddoc-aware diffs).
    """
    base = _resolve_library_dir()
    if base is None:
        return {"status": "ok", "library_dir": None, "count": 0, "commits": []}
    base = base.resolve()
    if not (base / ".git").exists() or not _git_available():
        return {
            "status": "ok",
            "library_dir": str(base),
            "git_enabled": False,
            "count": 0,
            "commits": [],
        }
    fmt = "%H%x09%an%x09%aI%x09%s"  # tab-separated
    res = _git_run(base, "log", f"-{limit}", f"--pretty=format:{fmt}")
    commits: List[Dict[str, Any]] = []
    if res.returncode == 0 and res.stdout:
        for line in res.stdout.splitlines():
            parts = line.split("\t", 3)
            if len(parts) == 4:
                commits.append({
                    "commit": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "subject": parts[3],
                })
    return {
        "status": "ok",
        "library_dir": str(base),
        "git_enabled": True,
        "count": len(commits),
        "commits": commits,
    }


# ── Round 24 — token CRUD ───────────────────────────────────────────


_TOKEN_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")
_TOKEN_SCOPE_RE = re.compile(r"^(write|admin)$")
_TOKEN_ID_RE = re.compile(r"^tok_[0-9a-f]{8}$")


def _require_library() -> Path:
    base = _resolve_library_dir()
    if base is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "library_not_configured"},
        )
    return base.resolve()


@router.get("/tokens")
def list_write_tokens(request: Request) -> Dict[str, Any]:
    """List active + revoked write tokens (without secrets). Admin-gated.
    """
    _check_admin_token(request)
    base = _require_library()
    return {
        "status": "ok",
        "count": len(token_store.list_tokens(base)),
        "tokens": token_store.list_tokens(base),
    }


@router.post("/tokens")
def create_write_token(
    request: Request,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """Mint a new write token. Body: ``{name, scope?}``. Returns the
    plaintext secret **once** — store it client-side immediately;
    the server keeps only the SHA-256 hash. Admin-gated.
    """
    _check_admin_token(request)
    base = _require_library()
    name = (payload.get("name") or "").strip()
    if not _TOKEN_NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "error_code": "invalid_token_name",
                    "message": "name must match [A-Za-z0-9][A-Za-z0-9 _.-]{0,63}"},
        )
    scope = (payload.get("scope") or "write").strip()
    if not _TOKEN_SCOPE_RE.match(scope):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "error_code": "invalid_token_scope",
                    "message": "scope must be 'write' or 'admin'"},
        )
    minted = token_store.create_token(base, name, scope)
    return {"status": "ok", **minted}


@router.delete("/tokens/{tok_id}")
def revoke_write_token(tok_id: str, request: Request) -> Dict[str, Any]:
    """Soft-revoke (set ``revoked_at``); the record stays for audit.
    Admin-gated."""
    _check_admin_token(request)
    if not _TOKEN_ID_RE.match(tok_id):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "error_code": "invalid_token_id"},
        )
    base = _require_library()
    rec = token_store.revoke_token(base, tok_id)
    if rec is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error_code": "token_not_found", "id": tok_id},
        )
    return {"status": "ok", "token": rec}
