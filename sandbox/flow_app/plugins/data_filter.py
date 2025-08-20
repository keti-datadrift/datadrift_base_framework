import pluggy
from flow_app.hooks import hookspec

@pluggy.HookimplMarker("flow_app")
def run_module(data):
    print("데이터 필터링 모듈 실행 중...")
    # 'value' 열이 15보다 큰 행만 필터링
    filtered_data = data[data['value'] > 15]
    return filtered_data