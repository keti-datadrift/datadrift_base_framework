from pathlib import Path
import streamlit as st
from core.state import set_mode
from core.constants import DEFAULT_ARTIFACTS_DIR
from services import dvc_cli

from core.state import set_mode
from core.constants import (
    DEFAULT_DATA_ROOT, DEFAULT_ARTIFACTS_DIR, UPLOADS_DIR,
    WIDTH_STRETCH, APP_TITLE
)
from services import dvc_cli
from services.dataset_manager import (
    save_uploaded_zip, extract_zip, track_and_commit_dataset,
    ensure_data_branch
)


def _sync_art_dir_from_sidebar():
    # 사이드바 입력값을 중앙 키로만 반영 (다른 위젯 키는 건드리지 않음)
    st.session_state["art_dir_path"] = st.session_state.get("art_dir", st.session_state["art_dir_path"])

def render_sidebar():
    st.title("⚙️ 설정")
    project_input = st.text_input("프로젝트 루트", value=st.session_state.project_root, help="dvc.yaml과 params.yaml이 있는 경로")
    st.session_state.project_root = str(Path(project_input).resolve())
    project_root = Path(st.session_state.project_root)

    # Mode toggle
    mode = st.radio("모드", ("Easy", "Advanced"), horizontal=True, index=(0 if st.session_state.mode=="Easy" else 1))
    set_mode(mode)

    st.subheader("🌐 DVC Remote")
    st.text_input("원격 이름", key="remote_name")
    st.text_input("원격 URL", key="remote_url")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("원격 추가/수정"):
            if st.session_state.remote_url:
                out = dvc_cli.remote_list(project_root)
                if st.session_state.remote_name in (out.stdout or ""):
                    dvc_cli.remote_modify(st.session_state.remote_name, st.session_state.remote_url, project_root)
                else:
                    dvc_cli.remote_add_default(st.session_state.remote_name, st.session_state.remote_url, project_root)
                st.success("원격 설정 완료")
            else:
                st.warning("원격 URL을 입력하세요")
    with c2:
        if st.button("dvc push"):
            dvc_cli.dvc_push(project_root)
    with c3:
        if st.button("dvc pull"):
            dvc_cli.dvc_pull(project_root)

    st.subheader("📦 데이터 업로드 & 버전관리")
    dataset_name = st.text_input("데이터셋 이름", value="dataset")
    uploaded = st.file_uploader("Zip 업로드", type=["zip"], accept_multiple_files=False)
    create_tag = st.text_input("Git 태그(선택)", value="")
    push_remote = st.checkbox("업로드 후 DVC push", value=True)

    if st.button("업로드 → dvc add → 커밋 → (옵션) push"):
        if not uploaded:
            st.warning("zip 파일을 선택하세요.")
        else:
            data_dir = project_root / DEFAULT_DATA_ROOT / dataset_name
            data_dir.parent.mkdir(parents=True, exist_ok=True)
            z = save_uploaded_zip(uploaded, project_root)
            extract_zip(z, data_dir)
            # 데이터 브랜치 유지 철학: 데이터셋별 브랜치로 전환/생성
            ensure_data_branch(dataset_name, project_root)
            track_and_commit_dataset(data_dir, project_root, f"Add dataset {dataset_name}", create_tag, push_remote)
            st.success("데이터 업로드 및 버전관리 완료")

    st.subheader("🧪 실험 실행 (dvc exp)")
    st.text_input("실험 이름", key="exp_name", value=st.session_state.exp_name or f"run-{st.session_state.get('exp_name') or ''}")
    st.checkbox("queue로 등록", key="queue_mode", value=st.session_state.queue_mode)
    if st.button("dvc exp run"):
        dvc_cli.exp_run(st.session_state.exp_name or "run", st.session_state.queue_mode, project_root)

    st.subheader("📁 경로 설정")
    # value는 중앙 키를 보여주고, 사용자가 바꾸면 on_change로 중앙 키만 갱신
    st.text_input(
        "아티팩트 폴더",
        value=st.session_state["art_dir_path"],
        key="art_dir",
        on_change=_sync_art_dir_from_sidebar,
    )
