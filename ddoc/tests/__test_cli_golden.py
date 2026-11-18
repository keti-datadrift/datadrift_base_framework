# tests/test_cli_golden.py
# Purpose: golden tests for ddoc CLI
# Notes:
# - We compare stdout to golden files (stable JSON/text).
# - For files created by commands (e.g., report.json), we compare their content to golden files.
# - If you intentionally change output formats, bump HOOKSPEC_VERSION and update goldens.

import json
from pathlib import Path

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def assert_equals_golden(actual: str, golden_path: Path):
    exp = read(golden_path)
    assert actual.strip() == exp.strip(), f"Mismatch vs golden: {golden_path}"

def test_help_lists_root_commands(runner, app_obj):
    """Ensure root commands are visible (not only 'plugin')."""
    result = runner.invoke(app_obj, ["--help"])
    assert result.exit_code == 0, result.output
    out = result.output
    # Expect core commands
    for cmd in ["eda", "transform", "drift", "reconstruct", "retrain", "monitor", "plugin"]:
        assert cmd in out, f"'--help' missing command: {cmd}"

def test_eda_golden(runner, app_obj, workdir, golden_dir, freeze_time):
    # Prepare input
    Path("in.txt").write_text("hello\nworld\n", encoding="utf-8")

    # Run command
    result = runner.invoke(app_obj, ["eda", "in.txt", "--modality", "table", "--out", "report.json"])
    assert result.exit_code == 0, result.output

    # Compare stdout
    assert_equals_golden(result.output, golden_dir / "eda.stdout.json")

    # Compare generated report.json (deterministic via freeze_time)
    assert_equals_golden(Path("report.json").read_text(encoding="utf-8"), golden_dir / "eda.report.json")

def test_transform_upper_golden(runner, app_obj, workdir, golden_dir):
    # Prepare input
    Path("in.txt").write_text("Abc\nxyz", encoding="utf-8")

    # Run command
    result = runner.invoke(app_obj, ["transform", "in.txt", "--transform", "text.upper", "--out", "out.txt"])
    assert result.exit_code == 0, result.output

    # Compare stdout
    assert_equals_golden(result.output, golden_dir / "transform_upper.stdout.json")

    # Compare file
    assert_equals_golden(Path("out.txt").read_text(encoding="utf-8"), golden_dir / "transform_upper.out.txt")

def test_drift_golden(runner, app_obj, workdir, golden_dir):
    # Prepare inputs
    Path("ref.txt").write_text("a\nb\nc\n", encoding="utf-8")
    Path("cur.txt").write_text("a\nb\nc\nd\n", encoding="utf-8")

    # Run command
    result = runner.invoke(app_obj, ["drift", "--ref", "ref.txt", "--cur", "cur.txt", "--detector", "toy", "--out", "drift.json"])
    assert result.exit_code == 0, result.output

    # Compare stdout
    assert_equals_golden(result.output, golden_dir / "drift.stdout.json")

    # Compare generated report
    assert_equals_golden(Path("drift.json").read_text(encoding="utf-8"), golden_dir / "drift.report.json")

def test_plugin_list_shows_builtins(runner, app_obj):
    """Plugin list should include ddoc_builtins (registered by core)."""
    result = runner.invoke(app_obj, ["plugin", "list"])
    assert result.exit_code == 0, result.output
    # Output is a dict pretty-printed by rich; we just check the string contains the name.
    assert "ddoc_builtins" in result.output, result.output