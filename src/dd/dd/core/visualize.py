import os
import json
import yaml
import matplotlib.pyplot as plt
from fpdf import FPDF
from weasyprint import HTML

DD_DIR = ".dd"
FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "fonts", "NanumGothicCoding-Regular.ttf")
DATA_LOG_FILE = os.path.join(DD_DIR, "data_log.json")
MODEL_LOG_FILE = os.path.join(DD_DIR, "model_log.json")
METADATA_FILE = os.path.join(DD_DIR, "metadata.yaml")

# 이미지 저장 경로
DATA_QUALITY_IMG = "data_quality.png"
MODEL_PERFORMANCE_IMG = "model_performance.png"

def plot_data_quality(data_log):
    versions = list(data_log.keys())
    missing_values = [data_log[v]["missing_values"] for v in versions]
    outliers = [data_log[v]["outliers"] for v in versions]
    quality_scores = [data_log[v]["quality_score"] for v in versions]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    axes[0].plot(versions, missing_values, marker='o', linestyle='-', color='r')
    axes[0].set_title("missing")
    axes[0].set_xticklabels(versions, rotation=45)

    axes[1].plot(versions, outliers, marker='o', linestyle='-', color='b')
    axes[1].set_title("outlier")
    axes[1].set_xticklabels(versions, rotation=45)

    axes[2].plot(versions, quality_scores, marker='o', linestyle='-', color='g')
    axes[2].set_title("data quality")
    axes[2].set_xticklabels(versions, rotation=45)

    plt.tight_layout()
    return fig

def plot_model_performance(model_log):
    versions = list(model_log.keys())
    accuracies = [model_log[v]["accuracy"] for v in versions]
    f1_scores = [model_log[v]["f1_score"] for v in versions]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(versions, accuracies, marker='o', linestyle='-', color='b', label="Accuracy")
    ax.plot(versions, f1_scores, marker='o', linestyle='-', color='g', label="F1 Score")
    ax.set_title("model performance")
    ax.set_xticklabels(versions, rotation=45)
    ax.legend()
    ax.grid()

    return fig

from weasyprint import HTML
def render_report(data_log, model_log, metadata):
    os.makedirs("outputs", exist_ok=True)
    
    data_fig = plot_data_quality(data_log)
    data_fig.savefig("outputs/data_quality.png", dpi=150)
    
    model_fig = plot_model_performance(model_log)
    model_fig.savefig("outputs/model_performance.png", dpi=150)
    
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>DD 프로젝트 상태 리포트</title>
        <style>
            @font-face {{
                font-family: 'NanumGothic';
                src: url('{FONT_PATH}');
            }}
            body {{
                font-family: 'NanumGothic', sans-serif;
                margin: 20px;
            }}
            h1, h2 {{
                color: #333;
                text-align: center;
                font-family: 'NanumGothic', sans-serif;  /* ✅ 강제 적용 */
            }}
            pre {{
                background-color: #f4f4f4;
                padding: 10px;
                border-radius: 5px;
            }}
            .image-container {{
                text-align: center;
                page-break-inside: avoid;  /* ✅ 이미지가 페이지를 넘지 않도록 설정 */
                display: block;
                margin-bottom: 20px;
            }}
            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 10px auto;
                max-height: 800px;
            }}
        </style>
    </head>
    <body>
        <h1>📊 DD 프로젝트 상태 리포트</h1>

        <h2>📜 프로젝트 메타데이터</h2>
        <pre>{json.dumps(metadata, indent=4, ensure_ascii=False)}</pre>

        <h2>📊 데이터 품질 변화</h2>
        <div class="image-container">
            <img src="{DATA_QUALITY_IMG}">
        </div>

        <h2>📝 모델 성능 변화</h2>  <!-- ✅ 이모지 제거 -->
        <div class="image-container">
            <img src="{MODEL_PERFORMANCE_IMG}">
        </div>
    </body>
    </html>
    """

    return html_content
    
def save_as_html(output_file, data_log, model_log, metadata):
    html_content = render_report(data_log, model_log, metadata)
    
    with open('outputs/' + output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"✅ 상태 리포트가 {'outputs/' + output_file}로 저장되었습니다.")

def save_as_pdf(output_file, data_log, model_log, metadata):
    html_content = render_report(data_log, model_log, metadata)
    
    with open('outputs/report.html', "w", encoding="utf-8") as f:
        f.write(html_content)
    
    HTML('outputs/report.html').write_pdf('outputs/' + output_file)
    
    print(f"✅ 상태 리포트가 {'outputs/' + output_file}로 저장되었습니다.")

def run(output_file):
    if not os.path.exists(DD_DIR):
        print("❌ `.dd` 디렉터리가 존재하지 않습니다. `dd init`을 먼저 실행하세요.")
        return

    with open(DATA_LOG_FILE, "r") as f:
        data_log = json.load(f)
    with open(MODEL_LOG_FILE, "r") as f:
        model_log = json.load(f)
    with open(METADATA_FILE, "r") as f:
        metadata = yaml.safe_load(f)

    if output_file.endswith(".pdf"):
        save_as_pdf(output_file, data_log, model_log, metadata)
    elif output_file.endswith(".html"):
        save_as_html(output_file, data_log, model_log, metadata)
    else:
        print("❌ 지원되지 않는 파일 형식입니다. PDF 또는 HTML로 저장하세요.")