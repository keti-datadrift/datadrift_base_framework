"""Round 16-D (alpr R21 framework consolidation) — unit tests for the
`train` step kind added to the recipe DSL.

Covers:
- argv composition (params dict → JSON-serialized --params-json)
- step kind registration
- validator accepts the new kind
- step output JSON exposed via ${steps.<id>.json.*}
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from ddoc.core.recipe import (
    Recipe,
    RecipeError,
    _STEP_KINDS,
    _step_to_argv,
)


def test_train_step_registered_with_expected_options():
    assert "train" in _STEP_KINDS
    spec = _STEP_KINDS["train"]
    assert spec["argv"] == ["train"]
    options = spec["options"]
    assert options["train_path"] == "--train-path"
    assert options["trainer"] == "--trainer"
    assert options["model_out"] == "--model-out"
    assert options["params"] == "--params-json"
    assert spec.get("json_flag") is True


def test_train_step_argv_serializes_params_as_json():
    with_args = {
        "train_path": "/data/full_train",
        "trainer": "alpr-recognizer",
        "model_out": "/runs/J-1",
        "params": {"epochs": 50, "batch": 64, "device": "cpu"},
    }
    argv = _step_to_argv("train", with_args)
    # Subcommand prefix.
    assert argv[:1] == ["train"]
    # --json (json_flag) is always appended.
    assert "--json" in argv
    # Required options present.
    assert "--train-path" in argv and "/data/full_train" in argv
    assert "--trainer" in argv and "alpr-recognizer" in argv
    assert "--model-out" in argv and "/runs/J-1" in argv
    # Params dict → JSON-encoded string after --params-json.
    idx = argv.index("--params-json")
    params_serialized = argv[idx + 1]
    parsed = json.loads(params_serialized)
    assert parsed == {"epochs": 50, "batch": 64, "device": "cpu"}


def test_train_step_validates_in_recipe(tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text(textwrap.dedent("""\
        name: train_only
        steps:
          - id: train
            run: train
            with:
              train_path: /data
              trainer: alpr-recognizer
              model_out: /out
              params:
                epochs: 1
    """), encoding="utf-8")
    recipe = Recipe.load(p)
    issues = recipe.validate()
    assert issues == [], f"unexpected issues: {issues}"


def test_train_step_rejects_unknown_with_key(tmp_path):
    """Unknown `with` keys must error — catches typos like
    `trainner:` (sic) before runtime."""
    p = tmp_path / "r.yaml"
    p.write_text(textwrap.dedent("""\
        steps:
          - id: train
            run: train
            with:
              train_path: /data
              trainer: alpr-recognizer
              model_out: /out
              params: {}
              not_a_real_option: oops
    """), encoding="utf-8")
    recipe = Recipe.load(p)
    issues = recipe.validate()
    # validate() doesn't catch unknown keys — that happens at argv
    # build time. Verify _step_to_argv raises.
    with pytest.raises(RecipeError) as ei:
        _step_to_argv("train", {
            "train_path": "/data",
            "trainer": "alpr-recognizer",
            "model_out": "/out",
            "params": {},
            "not_a_real_option": "oops",
        })
    assert ei.value.code == "unknown_with_key"
