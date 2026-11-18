"""Visualization command"""
from .utils import get_pmgr


def vis():
    """
    Run GUI app
    """
    meta = get_pmgr().hook.vis_run()

    # 메인 앱에서 실행하는 구조
    '''
    for item in meta:
        if item.get("type") == "streamlit":
            app_path = item.get("app_path")
            if app_path:
                subprocess.Popen(["streamlit", "run", app_path])
    '''

