# BEFORE
# art_dir = Path(st.session_state.get('art_dir') or (Path(st.session_state.project_root) / 'artifacts'))
# st.text_input("아티팩트 폴더", value=str(art_dir), key="art_dir")
# art_dir = Path(st.session_state.art_dir)
from pathlib import Path
import streamlit as st
from services.artifacts import render_downloads

def _sync_art_dir_from_tab():
    st.session_state["art_dir_path"] = st.session_state.get("art_dir_tab", st.session_state["art_dir_path"])

def render_tab_artifacts():
    # 탭 위젯은 별도 키 사용 (중복 키 방지)
    st.text_input(
        "아티팩트 폴더",
        value=st.session_state["art_dir_path"],
        key="art_dir_tab",
        on_change=_sync_art_dir_from_tab,
    )

    art_dir = Path(st.session_state["art_dir_path"])
    if art_dir.exists():
        render_downloads(art_dir)
    else:
        st.info("아티팩트 폴더가 존재하지 않습니다. 경로를 확인하세요.")
