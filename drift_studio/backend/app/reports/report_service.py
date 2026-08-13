"""HTML / PDF report generation for ``drift_studio/backend``.

Round 19 — pdfkit (wkhtmltopdf wrapper) replaced with weasyprint.
Same PDF engine ddoc CLI's ``ddoc report render`` uses (Round 11),
so the two paths share rendering quality + system dependencies.
Removes the wkhtmltopdf binary requirement from the backend's
deployment story.

Future direction (deferred): full migration to ``ddoc serve
/report/render`` HTTP call. That requires unifying the data shape
between this module's backend-specific dicts and ddoc's modality
envelope — bigger refactor, scheduled for a later round.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATE_DIR = "app/reports/templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True,
)


def _render_pdf(html: str, pdf_path: str) -> Optional[str]:
    """Render HTML to PDF via weasyprint. Returns the path on success
    or ``None`` if rendering fails (e.g. weasyprint deps missing in
    a stripped container)."""
    try:
        from weasyprint import HTML
    except ImportError as e:
        logger.warning("PDF rendering disabled — weasyprint not installed: %s", e)
        return None
    try:
        HTML(string=html).write_pdf(pdf_path)
        return pdf_path
    except Exception as e:  # noqa: BLE001
        logger.warning("PDF rendering failed for %s: %s", pdf_path, e)
        return None


def generate_eda_report(data: dict, output_dir: str = "reports") -> dict:
    """일반 tabular EDA 리포트.

    data: {id, name, rows, cols, missing, summary}
    """
    os.makedirs(output_dir, exist_ok=True)
    template = env.get_template("eda_report.html")
    html = template.render(**data)

    html_path = os.path.join(output_dir, f"{data['id']}_eda.html")
    pdf_path = os.path.join(output_dir, f"{data['id']}_eda.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    pdf_path = _render_pdf(html, pdf_path)
    return {"html": html_path, "pdf": pdf_path}


def generate_zip_eda_report(dataset, eda: dict, output_dir: str = "reports") -> dict:
    """ZIP 전용 EDA 리포트 (트리 구조 + Roboflow EDA 포함)."""
    os.makedirs(output_dir, exist_ok=True)
    template = env.get_template("eda_zip_report.html")

    html = template.render(dataset=dataset, eda=eda)

    html_path = os.path.join(output_dir, f"{dataset.id}_zip_eda.html")
    pdf_path = os.path.join(output_dir, f"{dataset.id}_zip_eda.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    pdf_path = _render_pdf(html, pdf_path)
    return {"html": html_path, "pdf": pdf_path}
