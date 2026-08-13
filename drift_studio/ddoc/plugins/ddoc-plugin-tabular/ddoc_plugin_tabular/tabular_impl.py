"""Tabular EDA report renderer.

The plugin's only job is to *render reports* for envelopes shaped
like ``drift_studio/backend``'s tabular EDA output (``{name, rows,
cols, missing, summary, ...}``). It taps the ``report_render``
hookspec (firstresult=True) and intercepts only when the envelope
looks tabular; for any other shape it returns ``None`` so the
built-in Jinja renderer or other plugins handle it.

Recognition rule: ``modality == "tabular"`` *or* presence of any of
``rows`` / ``cols`` / a tabular ``summary`` (dict-of-dicts of
column→stat→value).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from ddoc.plugins.hookspecs import hookimpl
except ImportError:  # pragma: no cover
    def hookimpl(func):  # type: ignore[misc]
        return func


_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _looks_tabular(envelope: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(envelope, dict):
        return False
    if envelope.get("modality") == "tabular":
        return True
    # Heuristic: tabular envelopes carry rows/cols *and* a summary
    # without a modality field. Pure-modality EDA envelopes set
    # ``modality`` and lack rows/cols.
    has_table_shape = "rows" in envelope or "cols" in envelope
    no_modality = "modality" not in envelope
    return has_table_shape and no_modality


def _summary_is_table(summary: Any) -> bool:
    """A backend-style summary is ``{column_name: {stat: value}}``.
    Detect that shape so the template renders it as a real HTML
    table instead of a JSON blob."""
    if not isinstance(summary, dict) or not summary:
        return False
    for v in summary.values():
        if not isinstance(v, dict):
            return False
    return True


def _summary_stat_columns(summary: Dict[str, Dict[str, Any]]) -> list[str]:
    """Union of stat names across all columns, preserving stable
    order: prefer common pandas describe() ordering, then any extras
    sorted alphabetically."""
    preferred = ["count", "mean", "std", "min", "25%", "50%", "75%", "max",
                 "unique", "top", "freq"]
    seen: set[str] = set()
    for stats in summary.values():
        if isinstance(stats, dict):
            seen.update(stats.keys())
    ordered = [s for s in preferred if s in seen]
    extras = sorted(s for s in seen if s not in ordered)
    return ordered + extras


class TabularReportPlugin:
    """ddoc plugin: tabular EDA report renderer."""

    @hookimpl
    def report_render(
        self,
        drift_result: Optional[Dict[str, Any]],
        eda_result: Optional[Dict[str, Any]],
        format: str,
        output_path: str,
        cfg: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        # Drift envelopes never render through this plugin.
        if drift_result and not _looks_tabular(drift_result):
            return None
        envelope = eda_result if _looks_tabular(eda_result) else (
            drift_result if _looks_tabular(drift_result) else None
        )
        if envelope is None:
            return None

        # We support html and pdf; markdown falls through to ddoc's
        # built-in markdown renderer (which already handles flat
        # envelopes acceptably).
        fmt = (format or "").lower()
        if fmt not in ("html", "pdf"):
            return None

        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        summary = envelope.get("summary")
        summary_table = _summary_is_table(summary)
        ctx: Dict[str, Any] = {
            "title": cfg.get("title"),
            "name": envelope.get("name"),
            "rows": envelope.get("rows"),
            "cols": envelope.get("cols"),
            "files_analyzed": envelope.get("files_analyzed"),
            "missing": envelope.get("missing"),
            "missing_is_dict": isinstance(envelope.get("missing"), dict),
            "summary": summary if summary_table else None,
            "summary_text": (
                json.dumps(summary, indent=2, ensure_ascii=False, default=str)
                if summary and not summary_table
                else ""
            ),
            "summary_is_table": summary_table,
            "summary_stats": (
                _summary_stat_columns(summary) if summary_table else []
            ),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "raw_json": json.dumps(envelope, indent=2, ensure_ascii=False, default=str),
        }

        tpl = env.get_template("eda_report.html")
        html = tpl.render(**ctx)

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "html":
            out.write_text(html, encoding="utf-8")
            return {
                "status": "success",
                "format": "html",
                "output_path": str(out),
                "size_bytes": out.stat().st_size,
                "renderer": "ddoc-plugin-tabular",
            }

        # fmt == "pdf"
        try:
            from weasyprint import HTML
        except ImportError:
            return None  # let the built-in fallback (or another plugin) try
        HTML(string=html).write_pdf(str(out))
        return {
            "status": "success",
            "format": "pdf",
            "output_path": str(out),
            "size_bytes": out.stat().st_size,
            "renderer": "ddoc-plugin-tabular",
        }

    @hookimpl
    def ddoc_get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "ddoc-plugin-tabular",
            "version": "1.0.0",
            "implements": ["report_render"],
            "description": (
                "Tabular EDA report renderer. Recognizes envelopes with "
                "modality='tabular' or rows/cols+summary shape and emits "
                "an HTML/PDF report mirroring drift_studio/backend's "
                "EDA layout. Round 27 (Track B)."
            ),
        }
