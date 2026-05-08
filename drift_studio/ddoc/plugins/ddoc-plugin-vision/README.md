# ddoc-plugin-vision

CLIP-based vision drift / EDA plugin for ddoc.

## Hookimpls

- `eda_run` — incremental attribute analysis (9 image attributes:
  brightness, exposure, contrast, dynamic_range, colorfulness,
  edge_density, sharpness, entropy, gaussian_noise_level) + CLIP
  ViT-B/16 embeddings. Outputs cached under
  `attributes_image` / `embedding_image`.
- `drift_detect` — `0.45 · attribute_drift + 0.55 · embedding_drift`.
- `ddoc_get_metadata` — plugin introspection.

## `--detector` (Round-11)

| value | embedding_drift formula |
|---|---|
| `default` (CLI default) | weighted ensemble (current behaviour) |
| `ensemble` | same as `default` |
| `mmd` | normalized multi-scale MMD only |
| `mean_shift` | normalized centroid L2 shift only |
| `wasserstein` | normalized 1-D wasserstein only |
| `psi` | normalized PSI on top PCA components only |
| `cosine` | cosine distance only |

All values produce `embedding_drift ∈ [0, 1]` (the per-metric scores
are normalized against empirical thresholds before exposure). The
ensemble weights live in `vision_impl.py:_calculate_embedding_drift_ensemble`.

Unsupported `--detector` values return an error envelope with
`error_code: unsupported_detector`.

## Install

```bash
pip install -e plugins/ddoc-plugin-vision   # editable, monorepo dev
# or once published:
pip install ddoc-plugin-vision torch torchvision pillow
pip install 'git+https://github.com/openai/CLIP.git'
```
