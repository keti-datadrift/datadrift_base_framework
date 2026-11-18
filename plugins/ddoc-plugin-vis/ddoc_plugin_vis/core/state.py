import json
from pathlib import Path
import streamlit as st

from core.constants import DVC_PARAMS_FILE

class AppMode:
    EASY = "Easy"
    ADV = "Advanced"

DEFAULT_STATE = {
    "project_root": str(Path.cwd()),
    "mode": AppMode.EASY,
    "selected_dataset": "",
    "compare_left": "",
    "compare_right": "",
    "exp_name": "",
    "queue_mode": False,
    "remote_name": "storage",
    "remote_url": "",
    "art_dir_path": "",   # ✅ 중앙 경로 키
}

def init_session():
    for k, v in DEFAULT_STATE.items():
        st.session_state.setdefault(k, v)
    # project_root 기준 기본값 초기화
    if not st.session_state["art_dir_path"]:
        st.session_state["art_dir_path"] = str(Path(st.session_state["project_root"]) / "artifacts")

# --- Simple signals to sync Easy/Advanced ---

def set_mode(mode: str):
    st.session_state.mode = mode


def load_params_yaml_text(project_root: Path) -> str:
    p = project_root / DVC_PARAMS_FILE
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def save_params_yaml_text(project_root: Path, text: str):
    (project_root / DVC_PARAMS_FILE).write_text(text, encoding="utf-8")