"""ddoc-plugin-categorical — drift on dict-of-counts distributions.

Closes a shape gap in the plugin set: applications often compute
drift over categorical distributions (``color_distribution``,
``type_distribution``, ...) but ddoc's plugins only covered
vision / text / timeseries / audio. This plugin handles the
categorical case via jensen_shannon and overlap metrics.
"""

from .categorical_impl import CategoricalDriftPlugin  # noqa: F401
