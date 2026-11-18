import time
from pathlib import Path
import streamlit as st

from core.state import init_session, AppMode
from core.constants import APP_TITLE
from views.sidebar import render_sidebar
from views.tabs_dashboard import render_tab_dashboard
from views.tabs_data import render_tab_data
from views.tabs_artifacts import render_tab_artifacts
from views.tabs_pipeline import render_tab_pipeline
from views.tabs_terminal import render_tab_terminal
from views.tabs_about import render_tab_about

st.set_page_config(page_title=APP_TITLE, layout="wide")
init_session()

with st.sidebar:
    render_sidebar()

st.title(APP_TITLE)

# Tabs
TAB_LABELS = [
    "📊 실험 대시보드",
    "🗂 데이터 탐색 & 비교",
    "📥 아티팩트 / 다운로드",
    "🔎 파이프라인 추적",
    "🖥️ DVC 터미널",
    "ℹ️ About",
]

t1, t2, t3, t4, t5, t6 = st.tabs(TAB_LABELS)

with t1:
    render_tab_dashboard()
with t2:
    render_tab_data()
with t3:
    render_tab_artifacts()
with t4:
    render_tab_pipeline()
with t5:
    render_tab_terminal()
with t6:
    render_tab_about()
    
st.markdown("---")
st.caption(
    "Tip: 먼저 DVC Remote를 설정하고, 데이터 업로드→추적→커밋→(옵션)푸시 후 `params.yaml` 조정과 `dvc exp run`으로 반복 실험을 관리하세요."
)