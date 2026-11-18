"""``ddoc diff`` — verdict facade tests.

Covers the three contract pillars: modality sniffing, the built-in CSV
fallback, and the verdict/exit-code mapping (0=OK, 1=DRIFT, 2=BLIND).
"""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from ddoc.cli.commands.diff import (
    compute_verdict,
    csv_diff,
    sniff_modality,
)
from ddoc.cli.main import app

runner = CliRunner()


# ── sniffing ──────────────────────────────────────────────────────────


def test_sniff_csv_file(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("x\n1\n")
    kind, detail = sniff_modality(f)
    assert kind == "csv"
    assert detail["files"] == [str(f)]


def test_sniff_image_dir(tmp_path):
    (tmp_path / "one.jpg").write_bytes(b"\xff\xd8")
    (tmp_path / "two.png").write_bytes(b"\x89PNG")
    kind, _ = sniff_modality(tmp_path)
    assert kind == "vision"


def test_sniff_categorical_marker_wins(tmp_path):
    (tmp_path / "distributions.json").write_text("{}")
    (tmp_path / "extra.csv").write_text("x\n1\n")
    kind, detail = sniff_modality(tmp_path)
    assert kind == "categorical"
    assert detail["marker"] == "distributions.json"


def test_sniff_empty_dir_unknown(tmp_path):
    kind, _ = sniff_modality(tmp_path)
    assert kind == "unknown"


# ── builtin csv comparator ────────────────────────────────────────────


def _write_csv(path, rows):
    path.write_text("\n".join(rows) + "\n")
    return str(path)


def test_csv_diff_identical_is_zero(tmp_path):
    rows = ["price,color", "100,red", "120,blue", "110,red"]
    a = _write_csv(tmp_path / "a.csv", rows)
    b = _write_csv(tmp_path / "b.csv", rows)
    res = csv_diff([a], [b])
    assert res["overall_score"] == 0.0
    assert set(res["columns_compared"]) == {"price", "color"}


def test_csv_diff_shifted_scores_high(tmp_path):
    a = _write_csv(tmp_path / "a.csv", ["price", "100", "110", "105"])
    b = _write_csv(tmp_path / "b.csv", ["price", "300", "290", "310"])
    res = csv_diff([a], [b])
    assert res["overall_score"] > 0.5
    assert res["detector"] == "builtin:csv_js"


def test_csv_diff_no_shared_columns_raises(tmp_path):
    a = _write_csv(tmp_path / "a.csv", ["x", "1"])
    b = _write_csv(tmp_path / "b.csv", ["y", "1"])
    with pytest.raises(ValueError, match="no shared columns"):
        csv_diff([a], [b])


# ── verdict mapping ───────────────────────────────────────────────────


def test_verdict_ok():
    v, sev, _ = compute_verdict(
        {"overall_score": 0.01, "attribute_drifts": {"a": 0.02}},
        threshold=0.15, attr_threshold=0.25,
    )
    assert (v, sev) == ("OK", "none")


def test_verdict_drift_by_overall():
    v, sev, _ = compute_verdict(
        {"overall_score": 0.2, "attribute_drifts": {"a": 0.2}},
        threshold=0.15, attr_threshold=0.25,
    )
    assert (v, sev) == ("DRIFT", "medium")


def test_verdict_drift_by_single_attribute():
    # 평균은 조용한데 한 축만 강하게 드리프트 — 평균에 묻히면 안 된다.
    v, sev, top = compute_verdict(
        {"overall_score": 0.08, "attribute_drifts": {"a": 0.4, "b": 0.01}},
        threshold=0.15, attr_threshold=0.25,
    )
    assert (v, sev) == ("DRIFT", "high")
    assert top[0][0] == "a"


# ── e2e: exit codes + json purity ─────────────────────────────────────


def _mk_pair(tmp_path, ref_rows, cur_rows):
    ref, cur = tmp_path / "ref", tmp_path / "cur"
    ref.mkdir(); cur.mkdir()
    _write_csv(ref / "data.csv", ref_rows)
    _write_csv(cur / "data.csv", cur_rows)
    return ref, cur


def test_diff_e2e_ok_exit_0(tmp_path):
    rows = ["price", "100", "110", "105"]
    ref, cur = _mk_pair(tmp_path, rows, rows)
    result = runner.invoke(app, ["diff", str(ref), str(cur), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["verdict"] == "OK"
    assert payload["engine"] == "builtin"


def test_diff_e2e_drift_exit_1_and_pure_json(tmp_path):
    ref, cur = _mk_pair(
        tmp_path,
        ["price", "100", "110", "105"],
        ["price", "300", "290", "310"],
    )
    result = runner.invoke(app, ["diff", str(ref), str(cur), "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout.strip())  # 전체 stdout이 JSON 하나여야 한다
    assert payload["verdict"] == "DRIFT"
    assert payload["top_attributes"][0][0] == "price"


def test_diff_e2e_missing_path_blind_exit_2(tmp_path):
    result = runner.invoke(app, ["diff", str(tmp_path / "nope"), str(tmp_path), "--json"])
    assert result.exit_code == 2, result.output
    payload = json.loads(result.stdout.strip())
    assert payload["verdict"] == "BLIND"


def test_diff_e2e_unknown_kind_blind_exit_2(tmp_path):
    ref, cur = tmp_path / "ref", tmp_path / "cur"
    ref.mkdir(); cur.mkdir()
    (ref / "weird.xyz").write_text("?")
    (cur / "weird.xyz").write_text("?")
    result = runner.invoke(app, ["diff", str(ref), str(cur), "--json"])
    assert result.exit_code == 2, result.output
    assert json.loads(result.stdout.strip())["verdict"] == "BLIND"


# ── consultation report (--report) ────────────────────────────────────


def test_diff_report_csv_evidence(tmp_path):
    ref, cur = _mk_pair(
        tmp_path,
        ["price,color", "100,red", "110,red", "105,blue"],
        ["price,color", "300,green", "290,green", "310,green"],
    )
    note = tmp_path / "note.html"
    result = runner.invoke(app, ["diff", str(ref), str(cur), "--json",
                                 "--report", str(note)])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout.strip())
    assert payload["report_path"] == str(note)
    body = note.read_text(encoding="utf-8")
    assert "Drift Consultation Note" in body
    assert "DRIFT" in body
    assert "price" in body and "color" in body          # findings bars
    assert "Evidence" in body and "green" in body       # distribution shift
    assert "Prescription" in body


def test_diff_report_categorical_evidence(tmp_path):
    import sys as _sys
    _sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from fixtures.factories import make_pair_categorical
    ref, cur = make_pair_categorical(tmp_path, scenario="shifted")
    note = tmp_path / "note.html"
    result = runner.invoke(app, ["diff", str(ref), str(cur), "--json",
                                 "--report", str(note)])
    assert result.exit_code == 1, result.output
    body = note.read_text(encoding="utf-8")
    # Evidence pulled straight from the two distributions.json files.
    assert "color_distribution" in body
    assert "Evidence" in body


def test_diff_report_blind(tmp_path):
    note = tmp_path / "note.html"
    result = runner.invoke(app, ["diff", str(tmp_path / "nope"), str(tmp_path),
                                 "--json", "--report", str(note)])
    assert result.exit_code == 2
    body = note.read_text(encoding="utf-8")
    assert "BLIND" in body and "Reason" in body


def test_build_consultation_html_minimal():
    from ddoc.cli.commands.diff_report import build_consultation_html
    html_out = build_consultation_html({
        "verdict": "OK", "severity": "none", "overall_score": 0.01,
        "threshold": 0.15, "attr_threshold": 0.25,
        "top_attributes": [["a", 0.01]], "ref": "/r", "cur": "/c",
        "modality": "tabular", "engine": "builtin", "detector": "x",
        "raw": {"attribute_drifts": {"a": 0.01}}, "hints": [],
    })
    assert "<html>" in html_out and "OK" in html_out
