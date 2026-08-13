"""ddoc-plugin-evidently — statistical drift detector backed by Evidently.

R32 — second consumer of the `drift_detect` hookspec (after the
KETI-native plugins vision/text/timeseries/audio/categorical). Per
R29 decision: native plugins stay primary for keti workflows;
Evidently kicks in only when `detector="evidently:chi2"` /
`"evidently:wasserstein"` / etc. is explicitly requested.
"""
from .plugin import EvidentlyDriftPlugin

__all__ = ["EvidentlyDriftPlugin"]
