"""Calls the drift_detect hookimpl directly (no pluggy/ddoc-core required --
the hookimpl decorator falls back to identity when ddoc isn't importable, see
reference_engine_impl.py) to confirm dataset discovery -> ladder -> structured
output actually wires together, and that the detector self-filter matches
this repo's broadcast-and-self-filter convention. eda_run's cache-service
interaction needs ddoc core installed and is covered separately by the plan's
CLI smoke test, not here.
"""
import numpy as np
import pandas as pd
import yaml

from ddoc_plugin_reference_engine.reference_engine_impl import ReferenceEnginePlugin

EXPECTED_LEVELS = {"L0_고정기준선", "L1_전년동일병기", "L2_레짐재정의", "L3_계절분해", "L4_개입보정"}


def _write_dataset(root, name, dates, values, numeric_col="value"):
    ds_dir = root / name
    ds_dir.mkdir(parents=True)
    df = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), numeric_col: values})
    df.to_csv(ds_dir / "data.csv", index=False)
    config = {
        "modality": "timeseries", "csv_file": "data.csv",
        "timestamp_column": "date", "numeric_columns": [numeric_col],
    }
    (ds_dir / "ddoc.yaml").write_text(yaml.safe_dump(config))


def test_drift_detect_ignores_default_and_other_detectors(tmp_path, monkeypatch):
    """Round-11/13 broadcast+self-filter convention: this plugin is opt-in
    only via detector="reference_engine", it must NOT respond to "default"
    (ddoc-plugin-timeseries already owns that slot for this modality) or to
    an unrelated detector string."""
    monkeypatch.chdir(tmp_path)
    dates = pd.date_range("2023-01-01", "2026-08-12", freq="D")
    values = np.random.default_rng(1).normal(100, 5, size=len(dates))
    _write_dataset(tmp_path / "cur", "sales", dates, values)

    plugin = ReferenceEnginePlugin()
    for detector in ("default", "mmd", "", None):
        result = plugin.drift_detect(
            snapshot_id_ref="baseline", snapshot_id_cur="current",
            data_path_ref=str(tmp_path / "does_not_exist"), data_path_cur=str(tmp_path / "cur"),
            data_hash_ref="x", data_hash_cur="y",
            detector=detector, cfg={}, output_path=str(tmp_path / "out"),
        )
        assert result is None, f"should not engage for detector={detector!r}"


def test_drift_detect_end_to_end_without_ref_falls_back_to_last_30_days(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # EventStore()'s default root is Path.cwd()
    dates = pd.date_range("2023-01-01", "2026-08-12", freq="D")
    values = np.random.default_rng(1).normal(100, 5, size=len(dates))

    cur_root = tmp_path / "cur"
    _write_dataset(cur_root, "sales", dates, values)

    plugin = ReferenceEnginePlugin()
    result = plugin.drift_detect(
        snapshot_id_ref="baseline", snapshot_id_cur="current",
        data_path_ref=str(tmp_path / "does_not_exist"),
        data_path_cur=str(cur_root),
        data_hash_ref="x", data_hash_cur="y",
        detector="reference_engine", cfg={}, output_path=str(tmp_path / "out"),
    )

    assert result is not None
    assert result["modality"] == "timeseries_reference"
    assert result["detector"] == "reference_engine"
    assert "overall_score" in result and "attribute_drifts" in result  # envelope convention
    assert "sales/value" in result["results"]
    assert set(result["results"]["sales/value"]["levels"].keys()) == EXPECTED_LEVELS
    assert (tmp_path / "out" / "metrics.json").exists()
    assert "pending_candidate_events" in result


def test_drift_detect_uses_ref_dataset_to_bound_evaluation_window(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dates = pd.date_range("2023-01-01", "2026-08-12", freq="D")
    values = np.random.default_rng(2).normal(100, 5, size=len(dates))

    cur_root, ref_root = tmp_path / "cur", tmp_path / "ref"
    _write_dataset(cur_root, "sales", dates, values)
    _write_dataset(ref_root, "sales", dates[:-10], values[:-10])  # ref는 10일 더 이전 상태

    plugin = ReferenceEnginePlugin()
    result = plugin.drift_detect(
        snapshot_id_ref="baseline", snapshot_id_cur="current",
        data_path_ref=str(ref_root), data_path_cur=str(cur_root),
        data_hash_ref="x", data_hash_cur="y",
        detector="reference_engine", cfg={}, output_path=str(tmp_path / "out"),
    )

    window = result["results"]["sales/value"]["evaluation_window"]
    assert window["start"] == str(dates[-10].date())
    assert window["end"] == str(dates[-1].date())


def test_ddoc_supported_detectors_declares_registry_entry():
    plugin = ReferenceEnginePlugin()
    decl = plugin.ddoc_supported_detectors()
    assert decl["modality"] == "timeseries_reference"
    assert "reference_engine" in decl["supported"]
