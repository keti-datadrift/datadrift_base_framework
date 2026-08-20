"""One-off generator for the reference-engine demo fixture (Round 37).

Run ONCE, from anywhere (paths resolve relative to this file):

    python drift_studio/backend/scripts/generate_reference_engine_demo_fixture.py

Writes the committed, static fixture consumed by
app/routers/reference_engine_demo.py:

    backend/app/sample_data/reference_engine_demo/
      ref/toy_metrics/{ddoc.yaml,data.csv}
      cur/toy_metrics/{ddoc.yaml,data.csv}

Two numeric columns in ONE dataset (one ddoc.yaml lists both under
numeric_columns -- reference_engine_impl.py runs each independently
through the level0-4 ladder):

  - revenue: seasonal + weekend lift + noise, PLUS a permanent x1.5 step
    multiplier injected exactly at the evaluation window's start date
    (the last WINDOW_DAYS days of `cur` that are absent from `ref`).
    Expected: alert at every level.
  - visits: identical seasonal+weekend+noise construction, no injected
    change -- a natural continuation. Expected: quiet at every level.

`ref` is a literal row-truncated prefix of `cur` (same source dataframe,
fewer rows) so the two can never disagree on overlapping history.

~3 years total (not "exactly 2") so `history` -- everything strictly
before the evaluation window, per reference_functions.py's
level3_decomposition -- comfortably clears MIN_DAYS_FOR_STL=730 with
margin; exactly-2-years-minus-a-30-day-window would land right at that
threshold.

Deterministic (fixed RNG seeds) -- rerunning reproduces byte-identical
CSVs.
"""
import numpy as np
import pandas as pd
import yaml
from pathlib import Path

WINDOW_DAYS = 30
START, END = "2023-01-01", "2025-12-31"  # ~3 years

REVENUE_BASE = 10_000.0
VISITS_BASE = 5_000.0
SEASONAL_AMPLITUDE = 0.15   # +-15% smooth annual cycle
WEEKEND_LIFT = 0.10         # +10% on Sat/Sun
NOISE_SD = 0.05             # 5% multiplicative Gaussian noise
STEP_MULTIPLIER = 1.5       # revenue: +50% starting at the eval window

OUT_ROOT = Path(__file__).resolve().parent.parent / "app" / "sample_data" / "reference_engine_demo"


def _seasonal_weekday_noise(dates: pd.DatetimeIndex, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    doy = dates.dayofyear.values.astype(float)
    seasonal = 1.0 + SEASONAL_AMPLITUDE * np.sin(2 * np.pi * doy / 365.25)
    weekend = dates.dayofweek.isin([5, 6])
    weekday_mult = np.where(weekend, 1.0 + WEEKEND_LIFT, 1.0)
    noise = rng.normal(1.0, NOISE_SD, size=len(dates))
    return seasonal * weekday_mult * noise


def build_frame() -> pd.DataFrame:
    dates = pd.date_range(START, END, freq="D")
    window_start = dates[-WINDOW_DAYS]

    revenue_mult = _seasonal_weekday_noise(dates, seed=20260812)
    step = np.where(dates >= window_start, STEP_MULTIPLIER, 1.0)
    revenue = np.round(REVENUE_BASE * revenue_mult * step, 2)

    visits_mult = _seasonal_weekday_noise(dates, seed=20260813)  # independent stream, no step
    visits = np.round(VISITS_BASE * visits_mult).astype(int)

    return pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "revenue": revenue, "visits": visits})


def write_dataset(root: Path, df: pd.DataFrame) -> None:
    ds_dir = root / "toy_metrics"
    ds_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(ds_dir / "data.csv", index=False)
    config = {
        "modality": "timeseries",
        "csv_file": "data.csv",
        "timestamp_column": "date",
        "numeric_columns": ["revenue", "visits"],
    }
    (ds_dir / "ddoc.yaml").write_text(yaml.safe_dump(config, sort_keys=False))


def main():
    full = build_frame()
    ref = full.iloc[:-WINDOW_DAYS].reset_index(drop=True)  # everything before the eval window
    cur = full                                              # full series, step included

    write_dataset(OUT_ROOT / "ref", ref)
    write_dataset(OUT_ROOT / "cur", cur)
    print(f"wrote {len(ref)} ref rows + {len(cur)} cur rows -> {OUT_ROOT}")
    print(f"evaluation window: {cur['date'].iloc[-WINDOW_DAYS]} .. {cur['date'].iloc[-1]}")


if __name__ == "__main__":
    main()
