"""Drift Zoo — 각 케이스는 튜토리얼이자 회귀 테스트다.

세 케이스가 세 가지 다른 판정(DRIFT high / DRIFT / OK)을 내는 것까지
고정한다: 모든 것을 DRIFT라 우기는 탐지기가 되지 않도록.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ddoc.cli.main import app

ZOO = Path(__file__).parent.parent / "zoo"
runner = CliRunner()


def _make(case: str, out_dir: Path):
    spec = importlib.util.spec_from_file_location(
        f"zoo_{case}_make", ZOO / case / "make.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.make(out_dir)


@pytest.mark.parametrize("case,verdict,exit_code", [
    ("regime_shift", "DRIFT", 1),
    ("creeping_degradation", "DRIFT", 1),
    ("rhythm_not_drift", "OK", 0),
])
def test_zoo_case_verdict(tmp_path, case, verdict, exit_code):
    ref, cur = _make(case, tmp_path)
    result = runner.invoke(app, ["diff", str(ref), str(cur), "--json"])
    assert result.exit_code == exit_code, result.output
    payload = json.loads(result.stdout.strip())
    assert payload["verdict"] == verdict


def test_zoo_regime_shift_report_evidence(tmp_path):
    ref, cur = _make("regime_shift", tmp_path)
    note = tmp_path / "note.html"
    runner.invoke(app, ["diff", str(ref), str(cur), "--json",
                        "--report", str(note)])
    body = note.read_text(encoding="utf-8")
    assert "price" in body and "channel" in body and "Evidence" in body
