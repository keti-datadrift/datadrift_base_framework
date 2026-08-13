"""Reference-selection-function ladder (levels 0/1/2/3/4).

Round 34. Ported from a validated pilot (context_workplace/drift_fashion_pilot/
reference_functions.py, itself validated against a real fashion-industry
reconciliation practice) with two changes for this production target:

1. Level 3's hand-rolled circular-smoothing decomposition is replaced with
   statsmodels' STL (this repo already depends on statsmodels via
   ddoc-plugin-timeseries; the pilot hand-rolled it only because its sandbox
   lacked the dependency). STL is not a drop-in replacement: it requires a
   REGULAR frequency index, so _prepare_regular_series() reindexes and fills
   gaps before decomposition -- the pilot's rolling-mean approach never had
   to do this.
2. AlertResult gains `attribution_confidence`. Per the causal-inference
   limitations review (context_workplace/drift_tool_analysis.md 12부), calling
   an intervention-matched deviation "explained" overclaims certainty --
   level4 now reports it as a "설명 후보"(candidate explanation) with a
   confidence estimate (currently a simple count of past events of the same
   type; real placebo/negative-control checks are a documented follow-up,
   not built here).

Each level exposes the same shape (series, start, end, ...) -> AlertResult so
results are directly comparable across levels for the same checkpoint.
"""
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

Z_THRESHOLD = 3.0  # 효과크기 기반 컷오프 - p-value가 아니라 z-score 크기로 판단
REGIME_CALIBRATION_DAYS = 60  # 레벨2: 신규 레짐의 기준선을 세우는 데 필요한 최소 관측 기간
MIN_DAYS_FOR_STL = 2 * 365  # STL은 최소 2주기 권장 (연간 계절성이면 2년)


@dataclass
class AlertResult:
    level: str
    status: str  # "alert" | "quiet" | "deferred"
    z_score: float
    expected: float
    actual: float
    reason: str
    attribution_confidence: Optional[float] = None  # None=귀속 주장 없음, 있으면 0~1 대략치

    @property
    def alert(self) -> bool:
        return self.status == "alert"

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "status": self.status,
            "z_score": round(self.z_score, 3),
            "expected": None if self.expected != self.expected else round(self.expected, 3),  # NaN-safe
            "actual": round(self.actual, 3),
            "reason": self.reason,
            "attribution_confidence": self.attribution_confidence,
        }


def _window_actual(series: pd.DataFrame, start, end) -> float:
    mask = (series["date"] >= start) & (series["date"] <= end)
    return float(series.loc[mask, "value"].mean())


def _window_stats(series: pd.DataFrame, start, end):
    mask = (series["date"] >= start) & (series["date"] <= end)
    vals = series.loc[mask, "value"]
    return float(vals.mean()), float(vals.std())


def level0_fixed_baseline(series: pd.DataFrame, start, end, baseline_days=90) -> AlertResult:
    """레벨0: 최초 N일을 고정 기준선으로 영원히 사용."""
    baseline = series.iloc[:baseline_days]["value"]
    expected, sd = float(baseline.mean()), float(baseline.std())
    actual = _window_actual(series, start, end)
    z = (actual - expected) / sd if sd > 0 else 0.0
    status = "alert" if abs(z) > Z_THRESHOLD else "quiet"
    return AlertResult("L0_고정기준선", status, z, expected, actual,
                        f"최초 {baseline_days}일 평균({expected:.1f}) 대비 고정 비교")


def _shifted_window_stats(series, start, end, days_back):
    shifted_start, shifted_end = start - pd.Timedelta(days=days_back), end - pd.Timedelta(days=days_back)
    return _window_stats(series, shifted_start, shifted_end)


def level1_yoy_dual_basis(series: pd.DataFrame, start, end) -> AlertResult:
    """레벨1: 전년 대비를 '동일 날짜(365일 전)'와 '동일 요일(364일=52주 전, 요일 보존)'
    두 기준으로 병기하고, 상충하면 판정을 유보한다 (실제 소매업 대사 관행 기반)."""
    actual = _window_actual(series, start, end)

    exp_date, sd_date = _shifted_window_stats(series, start, end, days_back=365)
    z_date = (actual - exp_date) / sd_date if sd_date > 0 else 0.0

    exp_dow, sd_dow = _shifted_window_stats(series, start, end, days_back=364)
    z_dow = (actual - exp_dow) / sd_dow if sd_dow > 0 else 0.0

    alert_date, alert_dow = abs(z_date) > Z_THRESHOLD, abs(z_dow) > Z_THRESHOLD
    same_sign = (z_date > 0) == (z_dow > 0)

    if alert_date != alert_dow or not same_sign:
        status = "deferred"
        reason = f"동일날짜기준(z={z_date:+.2f}) vs 동일요일기준(z={z_dow:+.2f}) 상충 -> 판정 유보"
    elif alert_date and alert_dow:
        status = "alert"
        reason = f"두 기준 모두 이탈 동의: 동일날짜 z={z_date:+.2f}, 동일요일 z={z_dow:+.2f}"
    else:
        status = "quiet"
        reason = "두 기준 모두 정상 범위 동의"

    return AlertResult("L1_전년동일병기", status, z_date, exp_date, actual, reason)


def level2_regime_redefinition(series: pd.DataFrame, start, end, regime_log: pd.DataFrame, series_name: str) -> AlertResult:
    """레벨2: 등록된 '영구 레짐 재정의' 이벤트 이후로는 기준선 자체를 그 시점 이후
    데이터로 다시 세운다. 레벨4(일시적·원상복귀 개입)와 달리 원래 기준선으로 돌아가지
    않는다는 것을 전제한다 (예: 플랫폼 이관으로 인한 영구적 지표 수준 변화)."""
    applicable = regime_log[
        (regime_log["series"] == series_name)
        & (pd.to_datetime(regime_log["effective_date"]) <= pd.Timestamp(start))
    ]
    if applicable.empty:
        base = level0_fixed_baseline(series, start, end)
        return AlertResult("L2_레짐재정의", base.status, base.z_score, base.expected, base.actual,
                            "등록된 레짐 전환 없음 -> 고정기준선과 동일하게 판단")

    effective_date = pd.to_datetime(applicable.iloc[0]["effective_date"])
    description = applicable.iloc[0]["description"]
    calibration_end = effective_date + pd.Timedelta(days=REGIME_CALIBRATION_DAYS)

    if pd.Timestamp(start) < calibration_end:
        actual = _window_actual(series, start, end)
        return AlertResult("L2_레짐재정의", "deferred", 0.0, float("nan"), actual,
                            f"{description} 이후 신규 기준 확립 중 (최소 {REGIME_CALIBRATION_DAYS}일 관측 필요)")

    calibration = series[(series["date"] >= effective_date) & (series["date"] < calibration_end)]
    expected, sd = float(calibration["value"].mean()), float(calibration["value"].std())
    actual = _window_actual(series, start, end)
    z = (actual - expected) / sd if sd > 0 else 0.0
    status = "alert" if abs(z) > Z_THRESHOLD else "quiet"
    return AlertResult("L2_레짐재정의", status, z, expected, actual,
                        f"{description} 이후 신규 기준선({expected:.1f}) 대비 비교")


def _prepare_regular_series(history: pd.DataFrame) -> pd.Series:
    """STL은 규칙적인(결측 없는) 일별 인덱스가 필요하다 -- 원본 파일럿의
    rolling-mean 방식과 달리 드롭인 교체가 아니므로 결측일을 명시적으로 채운다."""
    s = history.set_index("date")["value"].sort_index()
    full_index = pd.date_range(s.index.min(), s.index.max(), freq="D")
    return s.reindex(full_index).interpolate(limit_direction="both")


def _decompose(history: pd.DataFrame):
    """STL 분해: 추세 Series 전체, day-of-year 평균 계절성분, 잔차 표준편차를 반환.
    데이터가 STL 권장 최소치(2주기)보다 짧으면 계절성 없이 추세만 반환(점진적 성능저하)."""
    s = _prepare_regular_series(history)

    if len(s) < MIN_DAYS_FOR_STL:
        window = max(min(len(s), 30), 1)
        trend = s.rolling(window, center=True, min_periods=1).mean()
        doy_seasonal = pd.Series(0.0, index=range(1, 367))
        residual_sd = float(np.nanstd((s - trend).values))
        return trend, doy_seasonal, residual_sd

    stl_result = STL(s, period=365, robust=True).fit()
    trend = stl_result.trend
    doy_seasonal = stl_result.seasonal.groupby(stl_result.seasonal.index.dayofyear).mean()
    residual_sd = float(np.nanstd(stl_result.resid.values))
    return trend, doy_seasonal, residual_sd


def _classical_decompose(history: pd.DataFrame):
    trend, doy_seasonal, residual_sd = _decompose(history)
    last_trend = float(trend.dropna().iloc[-1]) if trend.notna().any() else float(history["value"].mean())
    return doy_seasonal, last_trend, residual_sd


def level3_decomposition(series: pd.DataFrame, start, end, history_end=None) -> AlertResult:
    """레벨3: 추세+연간계절성(STL)을 분해하고 잔차로만 비교."""
    history = series[series["date"] < (history_end or start)]
    doy_seasonal, last_trend, residual_sd = _classical_decompose(history)
    window = series[(series["date"] >= start) & (series["date"] <= end)]
    seasonal_for_window = window["date"].dt.dayofyear.map(doy_seasonal).fillna(0.0)
    expected_vals = last_trend + seasonal_for_window.values
    residual = window["value"].values - expected_vals
    z = float(np.mean(residual) / residual_sd) if residual_sd > 0 else 0.0
    status = "alert" if abs(z) > Z_THRESHOLD else "quiet"
    return AlertResult("L3_계절분해", status, z, float(expected_vals.mean()), float(window["value"].mean()),
                        "추세+연간계절성(STL) 분해 후 잔차로 비교")


def level4_intervention_adjusted(series: pd.DataFrame, start, end, intervention_log: pd.DataFrame,
                                  series_name: str, history_end=None) -> AlertResult:
    """레벨4: 레벨3 결과 위에, 활성 개입 로그(일시적·원상복귀 전제)가 있으면
    '설명 후보'로 표시한다(12부: "설명됨"은 확신을 과장하므로 쓰지 않음). 귀속
    신뢰도는 v1에서 동일 event_type의 과거 등록 건수로 단순 근사한다 -- 플라시보/
    음성대조 검정은 로드맵(미구현)."""
    base = level3_decomposition(series, start, end, history_end)
    active = intervention_log[
        (intervention_log["series"] == series_name)
        & (pd.to_datetime(intervention_log["start"]) <= pd.Timestamp(end))
        & (pd.to_datetime(intervention_log["end"]) >= pd.Timestamp(start))
    ]
    if base.alert and not active.empty:
        event = active.iloc[0]
        n_similar = int((intervention_log["event_type"] == event["event_type"]).sum())
        confidence = min(n_similar / 5.0, 1.0)
        reason = f"레벨3 편차 감지, 설명 후보 존재: {event['description']} (동일 유형 이벤트 {n_similar}건 근거)"
        return AlertResult("L4_개입보정", "quiet", base.z_score, base.expected, base.actual, reason,
                            attribution_confidence=confidence)
    reason = base.reason if not base.alert else "레벨3 편차, 등록된 개입 없음 -> 원인불명 드리프트"
    return AlertResult("L4_개입보정", base.status, base.z_score, base.expected, base.actual, reason)
