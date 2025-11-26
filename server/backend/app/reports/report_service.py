import os
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.join("app", "reports", "templates")

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True,
)


def generate_eda_report(data: Dict[str, Any], output_dir: str = "reports") -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)

    template = env.get_template("eda_report.html")
    html = template.render(**data)

    html_path = os.path.join(output_dir, f"{data['id']}_eda.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # PDF는 외부 wkhtmltopdf 의존성이 있어 환경에 따라 실패 가능하므로 생략하거나 TODO 처리
    pdf_path = ""

    return {"html": html_path, "pdf": pdf_path}
