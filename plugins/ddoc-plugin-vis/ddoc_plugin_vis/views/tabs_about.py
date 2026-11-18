"""views/tabs_terminal.py
Streamlit in-app DVC terminal with snippet groups and auto-refresh for exp show.
- Only allows commands beginning with `dvc` (safety)
- Beginner / Intermediate / Advanced snippet groups
- History (latest 50)
- If a command includes `exp run --run-all` (or `exp run`), trigger an app rerun to refresh dashboards
"""
from __future__ import annotations

import shlex
import time
from datetime import datetime
from pathlib import Path
from typing import List

import streamlit as st

from services.dvc_cli import run_shell

def render_tab_about() -> None:
    project_root = Path(st.session_state.project_root)
    st.subheader("ℹ️ About")
    st.markdown("- by JPark @ KETI, 2025")
    st.markdown("- This work was supported by Institute of Information & communications Technology Planning & Evaluation (IITP) grant funded by the Korea government(MSIT) (No. RS-2024-00337489, Development of data drift management technology to overcome performance degradation of AI analysis models)")

