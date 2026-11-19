# ddoc-plugin-audio

librosa-based audio drift / EDA plugin for ddoc.

## Hookimpls

- `eda_run` — per-file attribute analysis (rms_energy_mean,
  zcr_mean, spectral_centroid_mean) cached under `attributes_audio`.
  No embedding generation.
- `drift_detect` — Wasserstein distance on each of the three
  attribute distributions; `overall_score = mean(per-attribute)`.

## `--detector`

| value | drift formula |
|---|---|
| `default` (CLI default) | wasserstein on rms_energy/zcr/spectral_centroid (current behaviour) |
| `mmd` | alias for `default` |
| `wasserstein` | same as `default` |

Other values return an error envelope with `error_code:
unsupported_detector`. Embedding-based audio drift (e.g. via
HuBERT / wav2vec2) is not in scope for this plugin.

## Install

```bash
pip install -e packages/plugins/ddoc-plugin-audio
pip install librosa soundfile  # both already in plugin's deps
```
