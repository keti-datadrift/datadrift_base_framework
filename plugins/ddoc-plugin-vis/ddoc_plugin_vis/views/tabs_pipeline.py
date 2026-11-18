from pathlib import Path
import streamlit as st

from services.dvc_cli import dag_dot


def render_tab_pipeline():
    pr = Path(st.session_state.project_root)
    st.caption("dvc dag --dot 결과")
    st.markdown("- [ref] dot online viewer :: https://dreampuf.github.io/GraphvizOnline")
    cp = dag_dot(pr)
    if cp.returncode == 0 and cp.stdout:
        st.code(cp.stdout)
    else:
        st.info("DAG 정보를 가져오지 못했습니다. dvc.yaml을 확인하세요.")