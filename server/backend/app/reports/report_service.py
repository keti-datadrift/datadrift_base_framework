import os
from jinja2 import Environment, FileSystemLoader
import pdfkit  # wkhtmltopdf 설치되어 있지 않으면 PDF는 실패할 수 있음

TEMPLATE_DIR = "app/reports/templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True
)


def generate_eda_report(data: dict, output_dir="reports"):
    """
    일반 탭ular 등용 EDA 리포트
    data: {id, name, rows, cols, missing, summary}
    """
    os.makedirs(output_dir, exist_ok=True)
    template = env.get_template("eda_report.html")
    html = template.render(**data)

    html_path = os.path.join(output_dir, f"{data['id']}_eda.html")
    pdf_path = os.path.join(output_dir, f"{data['id']}_eda.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        pdfkit.from_string(html, pdf_path)
    except Exception:
        pdf_path = None

    return {"html": html_path, "pdf": pdf_path}


def generate_zip_eda_report(dataset, eda: dict, output_dir="reports"):
    """
    ZIP 전용 EDA 리포트 (트리 구조 + Roboflow EDA 포함)
    """
    os.makedirs(output_dir, exist_ok=True)
    template = env.get_template("eda_zip_report.html")

    html = template.render(dataset=dataset, eda=eda)

    html_path = os.path.join(output_dir, f"{dataset.id}_zip_eda.html")
    pdf_path = os.path.join(output_dir, f"{dataset.id}_zip_eda.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        pdfkit.from_string(html, pdf_path)
    except Exception:
        pdf_path = None

    return {"html": html_path, "pdf": pdf_path}