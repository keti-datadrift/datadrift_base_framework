# flow_app/hooks.py
import pluggy

hookspec = pluggy.HookspecMarker("flow_app")

@hookspec
def run_module(data):
    """
    모듈의 핵심 로직을 실행하는 후크.
    이전 모듈의 출력 데이터를 'data' 인자로 받습니다.
    """
    pass