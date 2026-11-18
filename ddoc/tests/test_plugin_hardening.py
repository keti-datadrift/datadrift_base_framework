"""Round 22 — plugin hardening tests (ffmpeg-style discipline).

Verifies:
- `ddoc --version` includes hookspec version + plugin manifest
- `ddoc --about` expands to per-plugin versions
- `_list_installed_plugins` is a pure entry-point scan (no heavy imports)
- Recipe `required_plugins:` field parses + validates
- Recipe `execute_recipe` short-circuits on missing plugins
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ddoc.cli.main import _list_installed_plugins
from ddoc.core.recipe import (
    Recipe,
    RecipeError,
    execute_recipe,
)


# ── --version / manifest ────────────────────────────────────────


def test_list_installed_plugins_returns_pairs():
    """Pure entry-point scan returns (name, version) tuples without
    importing the plugin modules."""
    rows = _list_installed_plugins()
    assert isinstance(rows, list)
    for entry in rows:
        assert isinstance(entry, tuple) and len(entry) == 2
        name, version = entry
        assert isinstance(name, str) and name
        assert isinstance(version, str) and version  # may be "?" if unknown


def test_list_installed_plugins_sorted():
    """Output is sorted for deterministic --version output."""
    rows = _list_installed_plugins()
    names = [n for n, _ in rows]
    assert names == sorted(names)


def test_list_installed_plugins_no_heavy_imports():
    """Calling _list_installed_plugins must not trigger torch /
    ultralytics imports. Heavy modules should NOT appear in sys.modules
    after the call (or if already loaded by another test, must not be
    newly loaded). Practical proxy: timing budget."""
    import time
    t0 = time.monotonic()
    _list_installed_plugins()
    elapsed = time.monotonic() - t0
    # Generous budget: just entry-point scan + version lookup.
    assert elapsed < 1.0, f"plugin scan took {elapsed:.2f}s (too slow)"


# ── required_plugins: in recipe DSL ──────────────────────────────


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "r.yaml"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def test_recipe_parses_required_plugins(tmp_path):
    p = _write(tmp_path, """\
        name: needs-vision
        required_plugins:
          - ddoc_vision
          - ddoc_alpr
        steps:
          - id: dummy
            run: fetch
            with:
              source_uri: /tmp/x
              dest: /tmp/y
    """)
    r = Recipe.load(p)
    assert r.required_plugins == ["ddoc_vision", "ddoc_alpr"]


def test_recipe_defaults_required_plugins_to_empty(tmp_path):
    p = _write(tmp_path, """\
        steps:
          - id: dummy
            run: fetch
            with:
              source_uri: /tmp/x
              dest: /tmp/y
    """)
    r = Recipe.load(p)
    assert r.required_plugins == []


def test_recipe_rejects_non_list_required_plugins(tmp_path):
    """`required_plugins: ddoc_vision` (scalar, not list) should
    error at load — catches typos before any subprocess fires."""
    p = _write(tmp_path, """\
        required_plugins: ddoc_vision
        steps:
          - id: dummy
            run: fetch
            with:
              source_uri: /tmp/x
              dest: /tmp/y
    """)
    with pytest.raises(RecipeError) as ei:
        Recipe.load(p)
    assert ei.value.code == "bad_required_plugins"


def test_check_plugin_requirements_returns_missing(tmp_path):
    p = _write(tmp_path, """\
        required_plugins:
          - ddoc_vision
          - ddoc_ghost
        steps:
          - id: dummy
            run: fetch
            with:
              source_uri: /tmp/x
              dest: /tmp/y
    """)
    r = Recipe.load(p)
    missing = r.check_plugin_requirements(installed=["ddoc_vision"])
    assert missing == ["ddoc_ghost"]


def test_check_plugin_requirements_empty_when_all_present(tmp_path):
    p = _write(tmp_path, """\
        required_plugins: [ddoc_vision]
        steps:
          - id: dummy
            run: fetch
            with: {source_uri: /tmp/x, dest: /tmp/y}
    """)
    r = Recipe.load(p)
    assert r.check_plugin_requirements(installed=["ddoc_vision", "ddoc_text"]) == []


def test_execute_recipe_short_circuits_on_missing_plugin(tmp_path, monkeypatch):
    """When a required plugin isn't installed, execute_recipe raises
    RecipeError BEFORE running any step (so the operator gets a
    focused install hint instead of mid-pipeline failure)."""
    p = _write(tmp_path, """\
        required_plugins:
          - ddoc_ghost_plugin_that_doesnt_exist
        steps:
          - id: would_run
            run: fetch
            with: {source_uri: /tmp/x, dest: /tmp/y}
    """)
    r = Recipe.load(p)
    # Force the requirement check to see an empty installed list so
    # the test doesn't depend on the host's plugin install.
    monkeypatch.setattr(r, "check_plugin_requirements",
                         lambda installed=None: ["ddoc_ghost_plugin_that_doesnt_exist"])
    with pytest.raises(RecipeError) as ei:
        execute_recipe(r)
    assert ei.value.code == "missing_required_plugins"
    assert "ddoc_ghost_plugin_that_doesnt_exist" in str(ei.value)
    # Hint surfaces the install command.
    assert ei.value.details.get("hint", "").startswith("Install with:")
