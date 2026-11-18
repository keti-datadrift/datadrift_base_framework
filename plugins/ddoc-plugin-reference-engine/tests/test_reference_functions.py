"""Same 4 checkpoints already validated in the pilot,
re-run against this repo's STL-based level3/4 to check
the algorithm swap didn't change the qualitative (status) behavior. Exact
z-scores are expected to differ from the pilot's hand-rolled decomposition --
only status is asserted, not specific numbers.
"""
import pandas as pd

from ddoc_plugin_reference_engine.reference_functions import (
    level0_fixed_baseline,
    level1_yoy_dual_basis,
    level3_decomposition,
    level4_intervention_adjusted,
)


def test_quiet_period_stays_quiet(synthetic_series):
    s = synthetic_series["basic_tees"]
    start, end = pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-30")
    assert level0_fixed_baseline(s, start, end).status == "quiet"
    assert level1_yoy_dual_basis(s, start, end).status == "quiet"
    assert level3_decomposition(s, start, end, history_end=start).status == "quiet"


def test_seasonal_peak_false_positive_resolved_by_higher_levels(synthetic_series):
    s = synthetic_series["basic_tees"]
    start, end = pd.Timestamp("2025-12-01"), pd.Timestamp("2025-12-30")
    assert level0_fixed_baseline(s, start, end).status == "alert", "L0은 계절성을 몰라 오탐해야 함"
    assert level1_yoy_dual_basis(s, start, end).status == "quiet", "작년 12월도 같은 성수기"
    assert level3_decomposition(s, start, end, history_end=start).status == "quiet", "STL 계절분해로 정상 인식"


def test_registered_campaign_suppressed_only_by_level4(synthetic_series, intervention_log):
    s = synthetic_series["swimwear"]
    start, end = pd.Timestamp("2026-07-14"), pd.Timestamp("2026-07-25")
    assert level0_fixed_baseline(s, start, end).status == "alert"
    assert level3_decomposition(s, start, end, history_end=start).status == "alert", "작년엔 없던 캠페인"

    l4 = level4_intervention_adjusted(s, start, end, intervention_log, "swimwear", history_end=start)
    assert l4.status == "quiet"
    assert l4.attribution_confidence is not None
    assert "설명 후보" in l4.reason, "12부: '설명됨'이 아니라 '설명 후보'로 표현해야 함"


def test_unregistered_drift_survives_every_level(synthetic_series, intervention_log):
    s = synthetic_series["cargo_pants"]
    start, end = pd.Timestamp("2025-09-15"), pd.Timestamp("2025-10-15")
    assert level0_fixed_baseline(s, start, end).status == "alert"
    assert level3_decomposition(s, start, end, history_end=start).status == "alert"

    l4 = level4_intervention_adjusted(s, start, end, intervention_log, "cargo_pants", history_end=start)
    assert l4.status == "alert", "등록된 개입이 없으므로 레벨4에서도 살아남아야 함"
    assert l4.attribution_confidence is None
