"""views/tabs_data.py
Data exploration with Easy / Advanced modes
- Easy: single dataset summary, safe preview, auto class distribution, CSV quick view
- Advanced: 2-way compare (revisions/paths), class distribution per side, CSV previews per side
"""
from __future__ import annotations

from pathlib import Path
import streamlit as st

from core.constants import DEFAULT_DATA_ROOT
from services.dataset_manager import (
    list_datasets,
    summarize_dataset,
    preview_samples,
    class_distribution,
    first_csv_preview,
)
from services.dvc_cli import dvc_pull
from services.git_cli import git_checkout
from utils.ui import metrics_row, class_bar_chart, csv_quick_view


def _dataset_select_box(project_root: Path, label: str):
    data_root = project_root / DEFAULT_DATA_ROOT
    options = [p.name for p in list_datasets(project_root)]
    if not options:
        st.info(f"{data_root} 아래에 데이터셋 폴더가 없습니다. 사이드바에서 업로드 하세요.")
        return None
    return st.selectbox(label, options)


def render_tab_data():
    project_root = Path(st.session_state.project_root)
    mode = st.session_state.get('mode', 'Easy')

    if mode == 'Easy':
        st.subheader("데이터셋 탐색 (Easy 모드)")
        one = _dataset_select_box(project_root, "데이터셋 선택")
        if one:
            ds_dir = project_root / DEFAULT_DATA_ROOT / one
            stats = summarize_dataset(ds_dir)
            metrics_row(stats)

            # Safe image preview
            imgs = preview_samples(ds_dir, limit=12)
            if imgs:
                st.caption("샘플 미리보기 (최대 12장)")
                st.image([str(p) for p in imgs])

            # Class distribution auto
            st.markdown("---")
            st.subheader("클래스 분포(Hint 기반)")
            class_counts = class_distribution(ds_dir)
            class_bar_chart(class_counts, title="클래스 분포")

            # CSV quick view (if exists)
            st.markdown("---")
            csv_info = first_csv_preview(ds_dir)
            if csv_info:
                path, df = csv_info
                st.caption(f"CSV: {path}")
                csv_quick_view(df)
            else:
                st.caption("CSV 파일을 찾지 못했습니다.")
        return

    # Advanced mode
    st.subheader("데이터셋 탐색 & 비교 (Advanced 모드)")
    with st.expander("리비전 체크아웃 + pull", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            left_rev = st.text_input("좌측 리비전/브랜치/태그", value=st.session_state.get('compare_left', ''))
        with col2:
            right_rev = st.text_input("우측 리비전/브랜치/태그", value=st.session_state.get('compare_right', ''))
        if st.button("(옵션) 순차 체크아웃 & dvc pull"):
            if left_rev:
                out = git_checkout(left_rev, project_root)
                if out.returncode == 0:
                    dvc_pull(project_root)
            if right_rev:
                out = git_checkout(right_rev, project_root)
                if out.returncode == 0:
                    dvc_pull(project_root)
            st.success("체크아웃 및 데이터 동기화 완료 (마지막 상태 기준)")

    st.markdown("---")
    st.subheader("폴더 2-way 비교")
    col1, col2 = st.columns(2)
    with col1:
        left_path = st.text_input("좌 비교 경로(폴더)", key="compare_left_path")
    with col2:
        right_path = st.text_input("우 비교 경로(폴더)", key="compare_right_path")

    if st.button("비교 실행"):
        lp = Path(left_path); rp = Path(right_path)
        if lp.exists() and rp.exists():
            ls = summarize_dataset(lp)
            rs = summarize_dataset(rp)
            st.write("### 좌측 요약")
            metrics_row(ls, label_prefix="좌/")
            st.write("### 우측 요약")
            metrics_row(rs, label_prefix="우/")

            # Class distributions
            st.markdown("---")
            lc = class_distribution(lp)
            rc = class_distribution(rp)
            col1, col2 = st.columns(2)
            with col1:
                st.write("좌측 클래스 분포")
                class_bar_chart(lc, title="좌측 클래스 분포")
            with col2:
                st.write("우측 클래스 분포")
                class_bar_chart(rc, title="우측 클래스 분포")

            # CSV quick views per side
            st.markdown("---")
            lcsv = first_csv_preview(lp)
            rcsv = first_csv_preview(rp)
            if lcsv:
                p, df = lcsv
                st.caption(f"좌측 CSV: {p}")
                csv_quick_view(df, title="좌측 CSV 미리보기")
            if rcsv:
                p, df = rcsv
                st.caption(f"우측 CSV: {p}")
                csv_quick_view(df, title="우측 CSV 미리보기")
        else:
            st.error("비교 경로가 올바르지 않습니다.")
