"""ddoc-plugin-categorical — drift on dict-of-counts distributions.

Round 26 (Track A) — closes the shape gap discovered in Round 25:
keti_veritas computes drift over categorical distributions
(``color_distribution``, ``type_distribution``, ...) but ddoc's
plugin set only covered vision / text / timeseries / audio. This
plugin handles the categorical case via jensen_shannon and overlap
metrics — the same math keti's ``DriftAnalyzer`` uses internally.
"""

from .categorical_impl import CategoricalDriftPlugin  # noqa: F401
