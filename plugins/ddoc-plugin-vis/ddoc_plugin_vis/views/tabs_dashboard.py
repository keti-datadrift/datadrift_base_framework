from pathlib import Path
import streamlit as st
from services.experiments import get_experiments_df, get_plots_specs, apply_experiment_and_sync_params
from utils.ui import dataframe


def render_tab_dashboard():
    project_root = Path(st.session_state.project_root)
    st.subheader("1) 실험 결과 테이블")
    df = get_experiments_df(project_root)
    if df is None or df.empty:
        st.info("실험 결과가 없습니다. dvc exp run 후 새로고침 하세요.")
    else:
        dataframe(df)
        st.markdown("---")
        st.caption("선택한 실험으로 워크스페이스를 되돌리고, 관련 params를 가급적 자동 동기화합니다.")
        choice = st.selectbox("적용할 실험 선택", df['Experiment'].tolist())
        if st.button("선택 실험 상태로 dvc exp apply + params sync"):
            sha = df.loc[df['Experiment'] == choice, 'SHA'].iloc[0]
            if sha and sha != 'workspace':
                ok = apply_experiment_and_sync_params(sha, project_root)
                if ok:
                    st.success("적용 및 params 동기화 완료")
                else:
                    st.error("적용 실패")
            else:
                st.info("workspace는 적용 대상이 아닙니다.")

    st.markdown("---")
    st.subheader("2) 메트릭/플롯 변화 (dvc plots diff --json)")
    specs = get_plots_specs(project_root)
    if isinstance(specs, list) and specs:
        for spec in specs:
            try:
                st.altair_chart(spec, width='stretch')
            except Exception:
                st.code(json.dumps(spec, indent=2, ensure_ascii=False))
    else:
        st.info("플롯 비교 데이터가 없습니다.")