# flow_app/plugins/visualizer.py

import pandas as pd
import pluggy
from dash import html

# name='visualizer_plugin'을 추가하여 고유한 이름 지정
@pluggy.HookimplMarker(project_name="flow_app")
def run_module(data):
    """
    Pandas DataFrame을 받아 Dash의 HTML 테이블로 반환합니다.
    """
    print("시각화 모듈 실행 중...")
    if not isinstance(data, pd.DataFrame):
        return html.Div("입력 데이터가 DataFrame이 아닙니다.", style={'color': 'red'})
    
    table_header = [html.Thead([html.Tr([html.Th(col) for col in data.columns])])]
    table_body = [html.Tbody([
        html.Tr([html.Td(data.iloc[i][col]) for col in data.columns])
        for i in range(len(data))
    ])]
    
    return html.Table(table_header + table_body)