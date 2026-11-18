# ddoc-plugin-timeseries

Time-series drift / EDA plugin for ddoc — pandas + statsmodels.

## Hookimpls

- `eda_run` — per-series attribute analysis (mean, variance,
  skewness, kurtosis, trend strength, seasonality strength,
  ADF / KPSS stationarity) cached under `attributes_timeseries`.
- `drift_detect` — `mean(|ref[m] - cur[m]| for m in [mean, variance,
  skewness, kurtosis])`. Bounded only by data magnitude; comparable
  across series within the same modality.

## `--detector` (Round-11)

| value | drift formula |
|---|---|
| `default` (CLI default) | abs Δ on mean/var/skew/kurt (current behaviour) |
| `mmd` | alias for `default` |
| `attributes` | same as `default` |

Other values return an error envelope with `error_code:
unsupported_detector`.

## Install

```bash
pip install -e plugins/ddoc-plugin-timeseries
# Already in plugin's deps: pandas, numpy, scipy, scikit-learn, statsmodels
```
