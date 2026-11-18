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

MAX_HISTORY = 50

SNIPPETS = {
    "초급": [
        "dvc --version",
        "dvc status",
        "dvc remote list",
        "dvc dag --dot",
        "dvc pull",
        "dvc push",
    ],
    "중급": [
        "dvc exp show -A --json",
        "dvc exp run -n run-$(date +%Y%m%d-%H%M%S)",
        "dvc exp run --queue -n queued-$(date +%H%M%S)",
        "dvc exp run --run-all",
        "dvc plots diff --json",
    ],
    "고급": [
        "dvc exp apply <rev>",
        "dvc exp remove <rev_or_name>",
        "dvc exp push",
        "dvc exp pull",
        "dvc repro",
    ],
}


def _append_history(entry: dict) -> None:
    hist = st.session_state.setdefault("terminal_history", [])
    hist.append(entry)
    if len(hist) > MAX_HISTORY:
        del hist[: len(hist) - MAX_HISTORY]


def _render_history() -> None:
    hist = st.session_state.get("terminal_history", [])
    if not hist:
        return
    st.markdown("---")
    st.subheader("히스토리")
    for h in reversed(hist):
        st.caption(f"[{h['ts']}] $ {h['cmd']}")
        st.markdown("**STDOUT**")
        st.code(h.get("stdout", "") or "(no stdout)")
        if h.get("stderr"):
            with st.expander("STDERR 보기"):
                st.code(h["stderr"]) 
        st.text(f"exit code: {h.get('returncode', 'NA')}")


def _looks_like_refresh_needed(cmd: str) -> bool:
    # Heuristic: refresh experiments if user runs exp-related commands
    tokens = cmd.split()
    if len(tokens) < 2:
        return False
    if tokens[0] != "dvc":
        return False
    if tokens[1] == "exp":
        # refresh on most experiment mutations
        return True
    if tokens[1] in {"repro", "pull", "push"}:
        return False
    return False


def render_tab_terminal() -> None:
    project_root = Path(st.session_state.project_root)
    st.subheader("🖥️ DVC 터미널")

    # Snippet groups
    col_left, col_right = st.columns([2, 1])
    with col_right:
        group = st.radio("명령어 스니펫 그룹", list(SNIPPETS.keys()), index=0, horizontal=False)
        chosen = st.selectbox("스니펫 선택", options=["(선택)"] + SNIPPETS[group], index=0)
        if chosen != "(선택)":
            st.session_state["terminal_cmd"] = chosen
        st.caption("필요 시 `<rev>`, `<rev_or_name>` 등을 실제 값으로 교체하세요.")

    with col_left:
        cmd = st.text_area(
            "명령 입력 (반드시 'dvc'로 시작)",
            key="terminal_cmd",
            height=120,
            placeholder="예: dvc exp show -A --json",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            run_btn = st.button("실행")
        with c2:
            clear_btn = st.button("입력 지우기")
        with c3:
            hist_clear_btn = st.button("히스토리 지우기")

    if clear_btn:
        st.session_state["terminal_cmd"] = ""
    if hist_clear_btn:
        st.session_state["terminal_history"] = []

    if run_btn:
        raw = (st.session_state.get("terminal_cmd") or "").strip()
        if not raw:
            st.warning("명령을 입력하세요.")
            return
        if not raw.startswith("dvc "):
            st.error("보안을 위해 'dvc'로 시작하는 명령만 허용됩니다.")
            return
        try:
            args: List[str] = shlex.split(raw)
        except Exception:
            st.error("명령 파싱 실패: 공백/인용부호를 확인하세요.")
            return

        cp = run_shell(args, project_root)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _append_history({
            "ts": ts,
            "cmd": raw,
            "returncode": cp.returncode,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
        })

        if cp.returncode == 0:
            st.success("명령이 성공적으로 실행되었습니다.")
        else:
            st.error(f"명령 실패 (exit {cp.returncode})")

        st.markdown("**STDOUT**")
        st.code(cp.stdout or "(no stdout)")
        if cp.stderr:
            st.markdown("**STDERR**")
            st.code(cp.stderr)

        # Auto-refresh experiments dashboard if needed
        if _looks_like_refresh_needed(raw):
            # 소폭 딜레이 후 전체 앱 리런 (exp show 테이블/플롯 최신화)
            time.sleep(0.3)
            st.rerun()

    _render_history()
