import os
from jinja2 import Environment, FileSystemLoader
import pdfkit  # or weasyprint

TEMPLATE_DIR = "app/reports/templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True
)

def generate_eda_report(data: dict, output_dir="reports"):
    os.makedirs(output_dir, exist_ok=True)

    template = env.get_template("eda_report.html")
    html = template.render(**data)

    html_path = os.path.join(output_dir, f"{data['id']}_eda.html")
    pdf_path = os.path.join(output_dir, f"{data['id']}_eda.pdf")

    # HTML 저장
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # PDF 변환
    try:
        pdfkit.from_string(html, pdf_path)
    except:
        pass  # PDF 실패해도 HTML만으로 충분

    return {
        "html": html_path,
        "pdf": pdf_path,
    }