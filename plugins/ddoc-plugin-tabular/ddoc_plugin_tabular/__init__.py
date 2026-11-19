"""ddoc-plugin-tabular — report rendering for tabular EDA envelopes.

Tabular EDA reports (`{name, rows, cols, missing, summary}`) were not
expressible through any ddoc template (which only knows the modality
shape). This plugin provides a Jinja template that renders the
tabular envelope, so callers can POST such data through
``ddoc /report/render`` instead of running their own renderer.
"""

from .tabular_impl import TabularReportPlugin  # noqa: F401
