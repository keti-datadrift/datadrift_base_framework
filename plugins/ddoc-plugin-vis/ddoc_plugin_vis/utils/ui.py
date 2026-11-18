# ================================
# File: utils/ui.py
# ================================
"""utils/ui.py
UI helpers for Streamlit with forward-proofed width API and small charts.
- Metric rows for extended modalities
- Class distribution bar chart (Altair)
- CSV preview table and quick charts
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence

import pandas as pd
import altair as alt
import streamlit as st

from core.constants import WIDTH_STRETCH, WIDTH_CONTENT


def metrics_row(stats: Dict, label_prefix: str = ""):
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{label_prefix}이미지", int(stats.get('num_images', 0)))
    c2.metric(f"{label_prefix}오디오", int(stats.get('num_audio', 0)))
    c3.metric(f"{label_prefix}비디오", int(stats.get('num_video', 0)))

    c4, c5, c6 = st.columns(3)
    c4.metric(f"{label_prefix}텍스트", int(stats.get('num_text', 0)))
    c5.metric(f"{label_prefix}CSV", int(stats.get('num_csv', 0)))
    c6.metric(f"{label_prefix}기타", int(stats.get('num_other', 0)))

    c7, c8, c9 = st.columns(3)
    c7.metric(f"{label_prefix}XML", int(stats.get('num_xml', 0)))
    c8.metric(f"{label_prefix}JSON", int(stats.get('num_json', 0)))
    c9.metric(f"{label_prefix}용량(GB)", stats.get('size_gb', 0.0))

    # Media summary (ffprobe)
    c10, c11 = st.columns(2)
    c10.metric(f"{label_prefix}오디오 길이(초)", stats.get('audio_seconds', 0.0))
    c11.metric(f"{label_prefix}비디오 길이(초)", stats.get('video_seconds', 0.0))


def dataframe(df: pd.DataFrame):
    st.dataframe(df, **WIDTH_STRETCH)


def class_bar_chart(class_counts: Dict[str, int], title: str = "클래스 분포"):
    if not class_counts:
        st.info("클래스 분포 데이터를 찾지 못했습니다.")
        return
    data = pd.DataFrame({"class": list(class_counts.keys()), "count": list(class_counts.values())})
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(x=alt.X("class:N", sort='-y', title="class"), y=alt.Y("count:Q", title="count"), tooltip=["class", "count"])
        .properties(title=title)
    )
    st.altair_chart(chart)


def csv_quick_view(df: pd.DataFrame, title: str = "CSV 미리보기", chart_cols: Optional[Sequence[str]] = None):
    st.subheader(title)
    dataframe(df.head(50))
    # Simple numeric chart (first 2 numeric columns)
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cols = list(chart_cols or num_cols[:2])
    if len(cols) >= 1:
        long = df.reset_index().melt(id_vars=['index'], value_vars=cols, var_name='series', value_name='value')
        line = (
            alt.Chart(long)
            .mark_line()
            .encode(x='index:Q', y='value:Q', color='series:N', tooltip=['index', 'series', 'value'])
            .properties(title="간단 라인 차트")
        )
        st.altair_chart(line)
