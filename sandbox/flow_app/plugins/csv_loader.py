# flow_app/plugins/csv_loader.py

import pandas as pd
import pluggy

# name='csv_loader_plugin'을 추가하여 고유한 이름 지정
@pluggy.HookimplMarker(project_name="flow_app")
def run_module(data):
    """CSV 파일을 읽어 DataFrame을 반환합니다."""
    print("CSV 로더 모듈 실행 중...")
    df = pd.read_csv('flow_app/data.csv')
    return df