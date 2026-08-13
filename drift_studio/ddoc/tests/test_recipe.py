"""Round-16 recipe layer — unit tests for parser, substitution,
validation, and a light smoke for end-to-end execution.
"""
from __future__ import annotations

import importlib.metadata as md
import json
import textwrap
from pathlib import Path

import pytest

from ddoc.core.recipe import (
    Recipe, RecipeError, _STEP_KINDS, _step_to_argv, _substitute,
    execute_recipe,
)


def _plugin_installed(name: str) -> bool:
    try:
        return any(ep.name == name for ep in md.entry_points(group="ddoc"))
    except Exception:
        return False


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "recipe.yaml"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


# ── Substitution ────────────────────────────────────────────────────


def test_substitute_vars_and_steps():
    ctx = {
        "vars": {"out": "/tmp/x", "name": "demo"},
        "env": {},
        "steps": {
            "drift": {
                "output": "/tmp/x/drift.json",
                "json": {"modality": "timeseries", "overall_score": 0.42, "summary": {"k": 1}},
            },
        },
    }
    assert _substitute("${vars.out}/file", ctx) == "/tmp/x/file"
    assert _substitute("${vars.name}-suffix", ctx) == "demo-suffix"
    # Whole-string single-ref → preserves type.
    assert _substitute("${steps.drift.json}", ctx) == ctx["steps"]["drift"]["json"]
    # Embedded ref → stringified.
    assert _substitute("score=${steps.drift.json.overall_score}", ctx) == "score=0.42"
    # Nested dict / list walks recursively.
    out = _substitute({"a": ["${vars.name}", "${vars.out}/y"]}, ctx)
    assert out == {"a": ["demo", "/tmp/x/y"]}


def test_substitute_unknown_step_ref_raises():
    ctx = {"vars": {}, "env": {}, "steps": {}}
    with pytest.raises(RecipeError) as ei:
        _substitute("${steps.nope.output}", ctx)
    assert ei.value.code == "unknown_step_ref"


# ── Argv build ──────────────────────────────────────────────────────


def test_step_to_argv_drift():
    argv = _step_to_argv(
        "analyze.drift",
        {
            "data_path_ref": "/tmp/r",
            "data_path_cur": "/tmp/c",
            "detector": "default",
            "quiet": True,
        },
    )
    assert argv[:2] == ["analyze", "drift"]
    assert "--data-path-ref" in argv and "/tmp/r" in argv
    assert "--data-path-cur" in argv and "/tmp/c" in argv
    assert "--detector" in argv and "default" in argv
    assert "--quiet" in argv
    assert "--json" in argv


def test_step_to_argv_unknown_kind():
    with pytest.raises(RecipeError) as ei:
        _step_to_argv("not.a.thing", {})
    assert ei.value.code == "unknown_step_kind"


def test_step_to_argv_unknown_with_key():
    with pytest.raises(RecipeError) as ei:
        _step_to_argv("analyze.drift", {"data_path_ref": "/a", "data_path_cur": "/b", "wat": 1})
    assert ei.value.code == "unknown_with_key"


# ── Recipe load + validate ─────────────────────────────────────────


def test_recipe_load_minimal(tmp_path):
    p = _write(tmp_path, """
        name: test
        steps:
          - id: gen
            run: examples.generate
            with: { modality: timeseries, out: /tmp/x, scenario: shifted }
    """)
    r = Recipe.load(p)
    assert r.name == "test"
    assert len(r.steps) == 1
    assert r.validate() == []


def test_recipe_validate_duplicate_id(tmp_path):
    p = _write(tmp_path, """
        steps:
          - id: a
            run: examples.generate
            with: { modality: timeseries, out: /tmp/a }
          - id: a
            run: examples.generate
            with: { modality: timeseries, out: /tmp/b }
    """)
    r = Recipe.load(p)
    issues = r.validate()
    assert any("duplicate id" in i for i in issues)


def test_recipe_validate_unknown_run(tmp_path):
    p = _write(tmp_path, """
        steps:
          - id: x
            run: not.real
            with: {}
    """)
    r = Recipe.load(p)
    issues = r.validate()
    assert any("unknown `run`" in i for i in issues)


def test_recipe_load_missing_file(tmp_path):
    with pytest.raises(RecipeError) as ei:
        Recipe.load(tmp_path / "nope.yaml")
    assert ei.value.code == "recipe_not_found"


# ── End-to-end ──────────────────────────────────────────────────────


def test_recipe_dry_run(tmp_path):
    p = _write(tmp_path, """
        name: dry
        vars:
          out: /tmp/dry
        steps:
          - id: gen
            run: examples.generate
            with:
              modality: timeseries
              out: "${vars.out}"
              scenario: shifted
          - id: drift
            run: analyze.drift
            with:
              data_path_ref: "${vars.out}/ref"
              data_path_cur: "${vars.out}/cur"
              quiet: true
    """)
    r = Recipe.load(p)
    result = execute_recipe(r, dry_run=True)
    assert result["status"] == "success"
    assert len(result["steps"]) == 2
    assert all(s["skipped"] for s in result["steps"])
    # Argv should still be fully resolved (substitution happens before
    # the dry-run gate).
    drift_argv = result["steps"][1]["argv"]
    assert any("/tmp/dry/ref" in a for a in drift_argv)


@pytest.mark.skipif(
    not _plugin_installed("ddoc_timeseries"),
    reason="ddoc-plugin-timeseries not installed",
)
def test_recipe_e2e_timeseries(tmp_path):
    """Run the canonical fetch-free recipe (gen → drift → report → export
    file) end-to-end with the timeseries plugin."""
    p = _write(tmp_path, f"""
        name: e2e
        workspace: {tmp_path / "wsp"}
        vars: {{ data_root: {tmp_path / "data"} }}
        steps:
          - id: gen_pair
            run: examples.generate
            with:
              modality: timeseries
              out: ${{vars.data_root}}
              scenario: shifted
          - id: drift
            run: analyze.drift
            with:
              data_path_ref: ${{vars.data_root}}/ref
              data_path_cur: ${{vars.data_root}}/cur
              quiet: true
          - id: report_md
            run: report.render
            with:
              input: ${{steps.drift.output}}
              out: {tmp_path}/report.md
              format: md
          - id: export_file
            run: export.drift_report
            with:
              input: ${{steps.drift.output}}
              target: file
              config: {{ out_dir: {tmp_path / "exports"} }}
    """)
    r = Recipe.load(p)
    result = execute_recipe(r, dry_run=False)
    assert result["status"] == "success", result
    steps = {s["id"]: s for s in result["steps"]}

    # gen_pair created ref/ and cur/.
    assert (tmp_path / "data" / "ref" / "toy_ts").exists()
    assert (tmp_path / "data" / "cur" / "toy_ts").exists()

    # drift produced an envelope and we auto-persisted it.
    drift_step = steps["drift"]
    assert drift_step["json"]["modality"] == "timeseries"
    assert drift_step["output"] is not None
    assert Path(drift_step["output"]).exists()

    # report_md wrote a markdown file.
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.md").stat().st_size > 0

    # export_file wrote a JSON under exports/.
    exports = list((tmp_path / "exports").glob("*.json"))
    assert len(exports) == 1
    payload = json.loads(exports[0].read_text())
    assert payload["protocol_version"] == "1.0"
    assert payload["drift"]["modality"] == "timeseries"


# ── 18.1: parallel block ────────────────────────────────────────────


def test_recipe_validate_parallel_block(tmp_path):
    p = _write(tmp_path, """
        steps:
          - id: pre
            run: examples.generate
            with: { modality: timeseries, out: /tmp/x, scenario: shifted }
          - parallel:
              - id: a
                run: examples.generate
                with: { modality: audio, out: /tmp/a, scenario: shifted }
              - id: b
                run: examples.generate
                with: { modality: text, out: /tmp/b, scenario: shifted }
    """)
    r = Recipe.load(p)
    assert r.validate() == []


def test_recipe_validate_parallel_duplicate_id(tmp_path):
    p = _write(tmp_path, """
        steps:
          - parallel:
              - id: dup
                run: examples.generate
                with: { modality: timeseries, out: /tmp/a }
              - id: dup
                run: examples.generate
                with: { modality: audio, out: /tmp/b }
    """)
    r = Recipe.load(p)
    issues = r.validate()
    assert any("duplicate id" in i for i in issues)


def test_recipe_validate_parallel_empty(tmp_path):
    p = _write(tmp_path, """
        steps:
          - parallel: []
    """)
    r = Recipe.load(p)
    issues = r.validate()
    assert any("parallel" in i for i in issues)


def test_recipe_dry_run_parallel(tmp_path):
    p = _write(tmp_path, """
        vars:
          out: /tmp/par
        steps:
          - parallel:
              - id: gen_a
                run: examples.generate
                with:
                  modality: timeseries
                  out: "${vars.out}/a"
                  scenario: shifted
              - id: gen_b
                run: examples.generate
                with:
                  modality: timeseries
                  out: "${vars.out}/b"
                  scenario: identical
          - id: gen_c
            run: examples.generate
            with:
              modality: timeseries
              out: "${vars.out}/c"
              scenario: shifted
    """)
    r = Recipe.load(p)
    result = execute_recipe(r, dry_run=True)
    assert result["status"] == "success"
    ids = [s["id"] for s in result["steps"]]
    assert ids == ["gen_a", "gen_b", "gen_c"]
    # All steps see substitution resolved.
    assert any("/tmp/par/a" in a for a in result["steps"][0]["argv"])
    assert any("/tmp/par/b" in a for a in result["steps"][1]["argv"])


@pytest.mark.skipif(
    not _plugin_installed("ddoc_timeseries"),
    reason="ddoc-plugin-timeseries not installed",
)
def test_recipe_e2e_parallel(tmp_path):
    """Parallel block runs two timeseries generations concurrently then
    a downstream report references one of them."""
    workspace = tmp_path / "wsp"
    p = _write(tmp_path, f"""
        workspace: {workspace}
        vars:
          out: {tmp_path / "data"}
        steps:
          - parallel:
              - id: gen_a
                run: examples.generate
                with:
                  modality: timeseries
                  out: "${{vars.out}}/a"
                  scenario: shifted
              - id: gen_b
                run: examples.generate
                with:
                  modality: timeseries
                  out: "${{vars.out}}/b"
                  scenario: identical
          - id: drift
            run: analyze.drift
            with:
              data_path_ref: "${{vars.out}}/a/ref"
              data_path_cur: "${{vars.out}}/a/cur"
              quiet: true
    """)
    r = Recipe.load(p)
    result = execute_recipe(r)
    assert result["status"] == "success", result
    steps = {s["id"]: s for s in result["steps"]}
    # Both parallel children reached returncode 0.
    assert steps["gen_a"]["returncode"] == 0
    assert steps["gen_b"]["returncode"] == 0
    # Downstream serial step succeeded with both parallel outputs visible.
    assert steps["drift"]["json"]["modality"] == "timeseries"
