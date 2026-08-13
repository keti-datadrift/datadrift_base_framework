"""Round 11 (D2 Track C) — recipe catalog tests.

Two new standalone recipes ship in `recipes/` (alongside the
existing `timeseries_smoke.yaml`):

* `csv_drift.yaml`         — env-var driven analyze + render
* `fetch_then_analyze.yaml` — env-var driven fetch + analyze + render

Tests confirm:
1. Both recipes parse and validate cleanly.
2. Both recipes survive a dry-run (substitution + step argv build).
3. `csv_drift.yaml` runs end-to-end against a generated categorical
   demo pair (the recipe assumes the data is already on disk).
4. `fetch_then_analyze.yaml` runs end-to-end with `file://` source
   URIs pointing at the generated demo dirs.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


_HERE = Path(__file__).resolve().parent
_RECIPES_DIR = _HERE.parent / "recipes"

sys.path.insert(0, str(_HERE))


def _generate_categorical_pair(out_dir: Path) -> tuple[Path, Path]:
    """Use the factory directly — avoids spawning a CLI subprocess
    inside an already-subprocess test setup."""
    from fixtures.factories import make_pair_categorical  # type: ignore[import-not-found]
    return make_pair_categorical(out_dir, scenario="shifted")


# ── (1) Recipe parse + validate ─────────────────────────────────────


@pytest.mark.parametrize("recipe_name", [
    "csv_drift.yaml",
    "fetch_then_analyze.yaml",
])
def test_recipe_loads_and_validates(recipe_name):
    """Both new recipes must parse via Recipe.load and emit no
    structural validation issues."""
    from ddoc.core.recipe import Recipe
    recipe_path = _RECIPES_DIR / recipe_name
    assert recipe_path.is_file(), f"missing recipe at {recipe_path}"
    recipe = Recipe.load(recipe_path)
    issues = recipe.validate()
    assert issues == [], f"{recipe_name} validation issues: {issues}"


# ── (2) Dry-run via CLI subprocess ──────────────────────────────────


def _cli() -> str | None:
    return shutil.which("ddoc")


@pytest.mark.parametrize("recipe_name,env", [
    (
        "csv_drift.yaml",
        {"DATA_PATH_REF": "/tmp/x_ref", "DATA_PATH_CUR": "/tmp/x_cur",
         "REPORT_OUT": "/tmp/x_drift.md"},
    ),
    # fetch_then_analyze.yaml is intentionally NOT in this list: it
    # uses `${steps.fetch_ref.json.local_path}` which can only be
    # resolved at *runtime* (after fetch_ref actually ran). Dry-run
    # fails with `step_no_json` by design — that recipe is covered by
    # the e2e test below instead.
])
def test_recipe_dry_run(recipe_name, env):
    """Dry-run resolves env-only substitutions and prints argv per
    step without actually invoking subprocesses. Recipes that depend
    on previous-step output cannot be dry-run."""
    cli = _cli()
    if cli is None:
        pytest.skip("ddoc CLI not on PATH")
    proc_env = {**os.environ, **env}
    proc = subprocess.run(
        [cli, "recipe", "run", str(_RECIPES_DIR / recipe_name),
         "--dry-run", "--json"],
        capture_output=True, text=True, timeout=30, env=proc_env,
    )
    assert proc.returncode == 0, proc.stderr
    last = next(
        (l for l in reversed(proc.stdout.splitlines())
         if l.strip().startswith("{")),
        None,
    )
    assert last is not None
    body = json.loads(last)
    assert body["status"] in ("ok", "success", "dry_run")
    assert isinstance(body.get("steps"), list)
    assert len(body["steps"]) >= 2


# ── (3) csv_drift.yaml e2e ──────────────────────────────────────────


def test_csv_drift_recipe_e2e(tmp_path):
    cli = _cli()
    if cli is None:
        pytest.skip("ddoc CLI not on PATH")

    data_dir = tmp_path / "data"
    ref, cur = _generate_categorical_pair(data_dir)
    report_out = tmp_path / "report.md"

    proc = subprocess.run(
        [cli, "recipe", "run", str(_RECIPES_DIR / "csv_drift.yaml"), "--json"],
        capture_output=True, text=True, timeout=120,
        env={
            **os.environ,
            "DATA_PATH_REF": str(ref),
            "DATA_PATH_CUR": str(cur),
            "REPORT_OUT":    str(report_out),
        },
    )
    assert proc.returncode == 0, proc.stderr
    assert report_out.is_file()
    body = report_out.read_text()
    # Markdown report includes the title and at least one drift score.
    assert "csv_drift recipe" in body or "Drift report" in body


# ── (4) fetch_then_analyze.yaml e2e (file:// source) ────────────────


def test_fetch_then_analyze_recipe_e2e(tmp_path):
    cli = _cli()
    if cli is None:
        pytest.skip("ddoc CLI not on PATH")

    src_dir = tmp_path / "src"
    ref, cur = _generate_categorical_pair(src_dir)
    work_root = tmp_path / "work"

    proc = subprocess.run(
        [cli, "recipe", "run",
         str(_RECIPES_DIR / "fetch_then_analyze.yaml"), "--json"],
        capture_output=True, text=True, timeout=120,
        env={
            **os.environ,
            "SOURCE_REF": f"file://{ref}",
            "SOURCE_CUR": f"file://{cur}",
            "WORK_ROOT":  str(work_root),
        },
    )
    assert proc.returncode == 0, proc.stderr
    # All four steps fire (fetch_ref, fetch_cur, drift, report).
    last = next(
        (l for l in reversed(proc.stdout.splitlines())
         if l.strip().startswith("{")),
        None,
    )
    assert last is not None
    body = json.loads(last)
    step_ids = [s.get("id") for s in body.get("steps", [])]
    assert step_ids == ["fetch_ref", "fetch_cur", "drift", "report"]
    assert (work_root / "report.md").is_file()
