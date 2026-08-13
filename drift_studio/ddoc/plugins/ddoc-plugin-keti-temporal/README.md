# ddoc-plugin-keti-temporal

**KETI research drift detector — Temporal Categorical Drift (R33)**.

The first KETI-original drift detector that goes beyond two-point
distribution comparison. Analyzes a *series* of categorical distributions
over time and classifies the temporal evolution into 4 patterns.

## Why this matters

ddoc-plugin-categorical (R26-A) answers "do these two distributions
differ?". Real keti operators ask harder questions:

| operator question | answers we give |
|---|---|
| "When did the camera go bad?" | `trend.argmax_idx` + `trend.z_anomalies` |
| "Is it gradually degrading?" | `patterns.linear_drift` + `trend.slope` |
| "Is it just a day-night rhythm?" | `patterns.cyclic` |
| "Is it stable enough for production?" | `patterns.stable` |

## Algorithm (research IP)

1. Aggregate baseline distributions into a single **reference**
   (mean of normalized inputs — so unequal sample sizes don't bias).
2. Per-step **distance** vs reference: Jensen-Shannon (default) or
   1-overlap.
3. **Trend** statistics on the resulting score series:
   - Linear regression slope
   - Max + argmax + cumulative
   - Z-score anomaly indices
4. **Pattern classification** from trend + raw scores:
   - `sudden_shift` ← any z-score > 2.0
   - `linear_drift` ← |slope| > 0.01
   - `cyclic`      ← |lag-1 autocorrelation| > 0.4 (positive = slow phase, negative = fast alternation)
   - `stable`      ← overall < 0.05 ∧ no anomalies ∧ |slope| < 0.01

All four flags are independent (a sudden_shift with linear_drift is
possible).

## Hookspec contract

Engages on `detector` starting with `keti:temporal_categorical`:
- `keti:temporal_categorical`            (default — JS divergence)
- `keti:temporal_categorical:js`         (alias)
- `keti:temporal_categorical:overlap`    (1 - histogram overlap)

Returns ddoc's standard `drift_detect` envelope shape — flows
through `report.render` / `export.drift_report` unchanged.

## Input

```yaml
cfg:
  baseline_categorical_series:
    - timestamp: "2026-05-09T00:00:00Z"
      distribution: {red: 30, blue: 10, white: 5}
    - timestamp: "2026-05-10T00:00:00Z"
      distribution: {red: 28, blue: 11, white: 6}
    ...
  # Optional — if omitted, first baseline entry becomes the ref and
  # rest become the steps to score.
  current_categorical_series:
    - timestamp: "..."
      distribution: {...}
```

## Output envelope

```json
{
  "status": "ok",
  "backend": "keti-temporal",
  "method": "jensen_shannon",
  "overall_score": 0.18,
  "attribute_drifts": {"distribution": 0.18},
  "step_scores": [
    {"timestamp": "2026-05-10T00:00:00Z", "score": 0.04},
    {"timestamp": "2026-05-11T00:00:00Z", "score": 0.08},
    ...
  ],
  "trend": {
    "slope": 0.012,
    "max_step": 0.45,
    "argmax_idx": 5,
    "cumulative": 1.23,
    "z_anomalies": [5]
  },
  "patterns": {
    "sudden_shift": true,
    "linear_drift": false,
    "cyclic": false,
    "stable": false
  }
}
```

## Direct product integration

Built to match keti_veritas R1 camera health snapshot workflow. The
existing endpoint `/api/v1/cameras/{id}/drift-report` can extend to
pass `detector="keti:temporal_categorical"` with N hourly
distributions instead of single 24h-vs-7d aggregate — operators get
**when** the camera went off-distribution, not just **that** it did.

## Install

```bash
pip install -e plugins/ddoc-plugin-keti-temporal
```

Verify discovery:
```bash
ddoc plugin list                  # ddoc_keti_temporal appears
ddoc plugin detectors             # keti:temporal_categorical listed
```
