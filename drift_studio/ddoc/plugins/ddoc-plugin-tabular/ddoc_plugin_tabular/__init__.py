"""ddoc-plugin-tabular — report rendering for tabular EDA envelopes.

Round 27 (Track B) — closes Round 25 shape gap #2: backend's tabular
EDA reports (`{name, rows, cols, missing, summary}`) were not
expressible through any ddoc template (which only knows the modality
shape). This plugin provides a Jinja template that renders the
tabular envelope, letting ``drift_studio/backend`` POST its data
through ``ddoc /report/render`` instead of running its own
weasyprint locally.
"""

from .tabular_impl import TabularReportPlugin  # noqa: F401
