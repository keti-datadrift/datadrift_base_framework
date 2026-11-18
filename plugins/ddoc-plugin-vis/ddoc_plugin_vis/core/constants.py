from pathlib import Path

VERSION = "2.0"
APP_TITLE = f"DataDrift Doctor for DataOps & MLOps ver{VERSION}"

DVC_METRIC_DIR = "dvclive"
DVC_PARAMS_FILE = "params.yaml"
DEFAULT_DATA_ROOT = "data"
DEFAULT_ARTIFACTS_DIR = "dvclive"
UPLOADS_DIR = "_uploads"

# UI: Streamlit 2025-12-31 이후 use_container_width 제거 권고 대응
WIDTH_STRETCH = dict(width="stretch")
WIDTH_CONTENT = dict(width="content")

# Params sync: Easy/Advanced 모드 공통 키 매핑 예시
# (사용자 프로젝트에 맞게 확장 가능)
PARAM_KEYS = {
    "dataset_name": ["data.dataset", "dataset", "data.name"],
    "dataset_path": ["data.path", "dataset_path"],
    "epochs": ["train.epochs", "epochs"],
    "imgsz": ["train.imgsz", "imgsz"],
    "batch": ["train.batch", "batch_size", "batch"],
}

# 브랜치 네이밍(데이터셋 중심 트리)
DATA_BRANCH_PREFIX = "data/"  # 예: data/d1, data/d2
MODEL_BRANCH_PREFIX = "model/" # 예: model/d1-20251017