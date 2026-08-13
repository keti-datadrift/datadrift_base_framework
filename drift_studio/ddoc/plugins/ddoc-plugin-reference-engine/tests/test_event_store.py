"""Event ontology store: register/load/confirm, and the auto-detection ->
candidate -> confirm pipeline (drift_tool_analysis.md 10.4)."""
import numpy as np
import pandas as pd

from ddoc_plugin_reference_engine.event_store import EventStore


def test_register_and_load_intervention(tmp_path):
    store = EventStore(project_root=tmp_path)
    store.register_intervention("swimwear", "2026-07-14", "2026-07-25", "test campaign")
    log = store.load_intervention_log()
    assert len(log) == 1
    assert log.iloc[0]["series"] == "swimwear"


def test_register_and_load_regime(tmp_path):
    store = EventStore(project_root=tmp_path)
    store.register_regime("online_mall", "2026-06-01", "platform migration")
    log = store.load_regime_log()
    assert len(log) == 1
    assert log.iloc[0]["series"] == "online_mall"


def test_unconfirmed_events_excluded_by_default(tmp_path):
    store = EventStore(project_root=tmp_path)
    store.register_intervention("x", "2026-01-01", "2026-01-01", "candidate", confirmed=False, proposed_by="auto_detection")
    assert store.load_intervention_log(confirmed_only=True).empty
    assert len(store.load_intervention_log(confirmed_only=False)) == 1


def test_confirm_event_makes_it_usable(tmp_path):
    store = EventStore(project_root=tmp_path)
    event_id = store.register_intervention("x", "2026-01-01", "2026-01-01", "candidate", confirmed=False)
    assert store.load_intervention_log(confirmed_only=True).empty

    assert store.confirm_event(event_id) is True
    assert len(store.load_intervention_log(confirmed_only=True)) == 1


def test_detect_candidate_events_flags_injected_spike(tmp_path):
    store = EventStore(project_root=tmp_path)
    dates = pd.date_range("2024-01-01", "2024-06-01", freq="D")
    rng = np.random.default_rng(0)
    values = rng.normal(100, 3, size=len(dates))
    values[-1] = 400.0  # 명백한 이상치를 마지막 날에 주입
    series = pd.DataFrame({"date": dates, "value": values})

    proposed = store.detect_candidate_events(series, "test_series", z_threshold=5.0)
    assert len(proposed) >= 1

    candidates = store.list_candidate_events()
    assert (candidates["event_type"] == "auto_detected_outlier").any()
    assert (candidates["confirmed"] == False).all()  # noqa: E712


def test_list_candidate_events_empty_when_nothing_pending(tmp_path):
    store = EventStore(project_root=tmp_path)
    assert store.list_candidate_events().empty
