"""Synthetic ground-truth fixtures, ported from the validated pilot
(context_workplace/drift_fashion_pilot/generate_synthetic_data.py). Same
injected scenarios: basic_tees (control), swimwear (registered campaign,
first occurrence in 2026), cargo_pants (unregistered permanent trend break).
"""
import numpy as np
import pandas as pd
import pytest

RNG = np.random.default_rng(42)
START, END = "2023-01-01", "2026-08-12"

MONTHLY_INDEX = {
    "basic_tees":  {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 0.95, 7: 0.9, 8: 0.9, 9: 1.0, 10: 1.0, 11: 1.15, 12: 1.3},
    "swimwear":    {1: 0.5, 2: 0.5, 3: 0.6, 4: 0.8, 5: 1.1, 6: 1.6, 7: 2.2, 8: 1.8, 9: 0.9, 10: 0.6, 11: 0.5, 12: 0.5},
    "cargo_pants": {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 0.95, 7: 0.9, 8: 0.95, 9: 1.2, 10: 1.2, 11: 1.05, 12: 1.0},
}
BASE = {"basic_tees": 100, "swimwear": 60, "cargo_pants": 80}
WEEKEND_LIFT = {"basic_tees": 0.10, "swimwear": 0.15, "cargo_pants": 0.10}
NOISE_SD = {"basic_tees": 0.05, "swimwear": 0.08, "cargo_pants": 0.06}

REGIME_BREAK_DATE = pd.Timestamp("2025-09-01")
CAMPAIGN_START, CAMPAIGN_END = pd.Timestamp("2026-07-14"), pd.Timestamp("2026-07-25")


def _trend(category, dates):
    if category != "cargo_pants":
        return np.ones(len(dates))
    days_since_start = (dates - dates[0]).days.values.astype(float)
    days_since_break = (dates - REGIME_BREAK_DATE).days.values.astype(float)
    pre = 1.0 - 0.0002 * days_since_start
    post = 1.25 * (1.0 + 0.0015 * np.clip(days_since_break, 0, None))
    return np.where(dates < REGIME_BREAK_DATE, pre, post)


def _campaign_multiplier(category, dates):
    if category != "swimwear":
        return np.ones(len(dates))
    in_campaign = (dates >= CAMPAIGN_START) & (dates <= CAMPAIGN_END)
    return np.where(in_campaign, 1.6, 1.0)


def _generate_series(category, dates):
    monthly = dates.month.map(MONTHLY_INDEX[category]).values
    weekend = dates.dayofweek.isin([5, 6])
    weekly = np.where(weekend, 1 + WEEKEND_LIFT[category], 1.0)
    trend = _trend(category, dates)
    campaign = _campaign_multiplier(category, dates)
    noise = RNG.normal(1.0, NOISE_SD[category], size=len(dates))
    value = BASE[category] * monthly * weekly * trend * campaign * noise
    return np.round(np.clip(value, 0, None), 1)


@pytest.fixture(scope="session")
def synthetic_series():
    dates = pd.date_range(START, END, freq="D")
    return {cat: pd.DataFrame({"date": dates, "value": _generate_series(cat, dates)}) for cat in BASE}


@pytest.fixture(scope="session")
def intervention_log():
    return pd.DataFrame([{
        "event_id": "iv_test1", "event_type": "marketing_campaign", "series": "swimwear",
        "start": str(CAMPAIGN_START.date()), "end": str(CAMPAIGN_END.date()),
        "description": "test campaign", "confirmed": True, "proposed_by": "human",
    }])


@pytest.fixture(scope="session")
def empty_regime_log():
    return pd.DataFrame(columns=["event_id", "series", "effective_date", "description", "confirmed", "proposed_by"])
