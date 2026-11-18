# ddoc-plugin-text

CLIP-based text drift / EDA plugin for ddoc.

## Hookimpls

- `eda_run` — text attribute analysis (length_chars, length_words,
  whitespace_ratio, special_char_ratio, stopword_ratio,
  vocab_diversity, readability) + optional CLIP embedding.
- `drift_detect` — `0.5 · attribute_drift + 0.5 · embedding_drift`
  when embeddings are available; attribute-only otherwise.
- `ddoc_get_metadata` — plugin introspection.

## `--detector` (Round-12)

| value | drift formula |
|---|---|
| `default` (CLI default) | 3-metric ensemble: 0.40·cosine + 0.40·MMD-multi-scale + 0.20·PSI-on-PCA. All components normalized to [0, 1]. |
| `mmd` | alias for `default` (CLI legacy default) |
| `ensemble` | alias for `default` |
| `cosine` | legacy: cosine distance only (Round-11 behaviour) |
| `mmd_only` | normalized multi-scale MMD only |
| `psi` | normalized PSI-on-PCA only |

Other values return an error envelope with `error_code:
unsupported_detector`. The ensemble shape (`embedding_drift_detailed`)
is preserved across strategies — only the picked `embedding_drift`
scalar changes.

## `--with-embeddings` (Round-10)

In path mode (no cache available), the plugin defaults to
attribute-only drift (overall_score = 0.5 · attr + 0.5 · 0). Pass
`--with-embeddings` to load CLIP inline and compute embedding drift
too — slower (~5 s + 600 MB RAM) but full cosine signal.

## Install

```bash
pip install -e plugins/ddoc-plugin-text   # editable, monorepo dev
pip install nltk
python -c "import nltk; [nltk.download(p) for p in ('punkt_tab','stopwords','averaged_perceptron_tagger')]"
# CLIP only needed when --with-embeddings or snapshot-mode embedding cache:
pip install 'git+https://github.com/openai/CLIP.git'
```
