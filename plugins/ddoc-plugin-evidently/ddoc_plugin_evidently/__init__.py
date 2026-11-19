"""ddoc-plugin-evidently — statistical drift detector backed by Evidently.

Implements the `drift_detect` hookspec alongside ddoc's native plugins
(vision/text/timeseries/audio/categorical/tabular), which stay the
default. Evidently kicks in only when `detector="evidently:chi2"` /
`"evidently:wasserstein"` / etc. is explicitly requested.
"""
from .plugin import EvidentlyDriftPlugin

__all__ = ["EvidentlyDriftPlugin"]
