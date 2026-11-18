"""ddoc-plugin-keti-temporal — temporal categorical drift detector.

Temporal Categorical Drift: analyze how a categorical distribution
EVOLVES over a series of time points (vs the point-in-time comparison
in ddoc-plugin-categorical). Distinguishes:

- Sudden shift  (concept change at a specific timestamp)
- Linear drift  (slow gradual change → significant slope)
- Cyclic       (recurring pattern — daily / weekly)
- Anomalous days (z-score outliers in the drift series)

Motivation: periodic health-snapshot workflows typically compare a
recent aggregate vs a baseline aggregate — operators want to see
*when* the source went off-distribution, not just *that* it did.
This plugin gives per-timestamp drifts + trend statistics.
"""
from .plugin import TemporalCategoricalDriftPlugin

__all__ = ["TemporalCategoricalDriftPlugin"]
