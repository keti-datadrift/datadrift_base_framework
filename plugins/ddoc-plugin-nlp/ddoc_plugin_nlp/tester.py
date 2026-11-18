import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Iterable
from nlp_impl import DDOCNlpPlugin

# --- 1. 환경 설정 및 로깅 모의 ---
# 실제 환경의 로깅을 모방하기 위해 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# 임시 입력 파일 및 출력 파일 경로 정의
INPUT_FILE = "test_input.txt"
OUTPUT_TOKENIZE = "test_output_tokenized.txt"
OUTPUT_NORMALIZE = "test_output_normalized.txt"

# 테스트를 위한 입력 데이터 생성
Path(INPUT_FILE).write_text(
    "Hello World. This is a test.\nAnother sentence. \n\nWith multiple spaces and newlines."
)
log.info(f"테스트 입력 파일 생성: {INPUT_FILE}")


# --- 2. Hook Specs 모의 (ddoc/plugins/hookspecs.py) ---
hookspec = pluggy.HookspecMarker("ddoc")
HOOKSPEC_VERSION = "1.0.0"

class HookSpecs:
    @hookspec
    def transform_apply(self, input_path: str, transform: str, args: Dict[str, Any], output_path: str) -> Optional[Dict[str, Any]]:
        """Apply a named transform and write result to output_path."""
        pass # 실제 구현은 플러그인에서 이루어집니다.

    @hookspec
    def ddoc_get_metadata(self) -> Optional[Dict[str, Any]]:
        """Returns structured metadata about the plugin."""
        pass

# 

# --- 4. PluginManager 모의 (ddoc/core/plugins.py) ---

class PluginManager:
    """ddoc/core/plugins.py의 핵심 기능만 모방"""
    def __init__(self) -> None:
        self.pm = pluggy.PluginManager("ddoc")
        self.pm.add_hookspecs(HookSpecs)
    
    @property
    def hook(self):
        return self.pm.hook
        
    def register_plugin_instance(self, plugin_obj: Any, name: Optional[str] = None):
        """인스턴스화된 플러그인 객체를 등록하는 함수 (load_entrypoints의 결과)"""
        try:
            self.pm.register(plugin_obj, name=name)
        except ValueError as e:
            log.info("중복 플러그인 감지: %s (%s)", name, e)

    def call_hook(self, hook_name: str, first_non_none: bool = True, **kwargs) -> Any:
        """Hook 호출 및 결과 반환"""
        hook = getattr(self.pm.hook, hook_name)
        results = hook(**kwargs)
        
        if first_non_none:
            for res in results:
                if res is not None:
                    return res
            return None
        return results

# 싱글톤 매니저와 초기화 함수
_PLUGIN_MANAGER: Optional[PluginManager] = None
def get_plugin_manager() -> PluginManager:
    global _PLUGIN_MANAGER
    if _PLUGIN_MANAGER is None:
        _PLUGIN_MANAGER = PluginManager()
        # ddoc_nlp 플러그인 인스턴스 등록 (Entry Point 로딩 시뮬레이션)
        # 이 부분이 이전 오류를 해결한 핵심 로직입니다!
        _PLUGIN_MANAGER.register_plugin_instance(DDOCNlpPlugin(), name="ddoc_nlp")
        log.info("--- DDOC Plugin Manager 초기화 완료 ---")
        log.info("등록된 플러그인: %s", [p.name for p in _PLUGIN_MANAGER.pm.get_plugins()])
    return _PLUGIN_MANAGER


# --- 5. CLI 명령어 실행 시뮬레이션 ---

def ddoc_transform(input_path: str, transform_name: str, output_path: str):
    """
    CLI 명령어: 'ddoc transform [OPTIONS] INPUT TRANSFORM' 실행을 시뮬레이션합니다.
    - INPUT: input_path
    - TRANSFORM: transform_name
    - OUTPUT: output_path (CLI 옵션으로 처리되었다고 가정)
    """
    log.info(f"\n[CLI 실행] ddoc transform {input_path} {transform_name} --output {output_path}")

    # 1. 플러그인 매니저 가져오기
    pm = get_plugin_manager()

    # 2. 'transform_apply' 훅 호출
    # first_non_none=True 설정으로, 변환을 처리한 첫 번째 플러그인의 결과를 얻습니다.
    result = pm.call_hook(
        hook_name='transform_apply',
        input_path=input_path,
        transform=transform_name,
        args={},  # CLI 옵션으로 전달되는 추가 인자
        output_path=output_path,
        first_non_none=True
    )

    # 3. 결과 처리
    if result is None:
        log.warning(f"명령어 실패: 등록된 플러그인 중 '{transform_name}'을 처리할 수 있는 플러그인이 없습니다.")
    elif result.get('ok'):
        log.info("성공: " + result.get('summary', '변환 성공'))
        log.info(f"결과 파일 확인: {output_path}")
        # 생성된 파일 내용 출력
        print("\n--- 결과 파일 내용 ---")
        print(Path(output_path).read_text(encoding="utf-8"))
        print("---------------------\n")
    else:
        log.error("변환 오류: " + result.get('error', '알 수 없는 오류'))


if __name__ == "__main__":
    # 1. 토큰화 변환 실행 시뮬레이션
    ddoc_transform(
        input_path=INPUT_FILE,
        transform_name="text.tokenize",
        output_path=OUTPUT_TOKENIZE
    )
    
    # 2. 정규화 변환 실행 시뮬레이션
    ddoc_transform(
        input_path=INPUT_FILE,
        transform_name="text.normalize",
        output_path=OUTPUT_NORMALIZE
    )

    # 3. 플러그인이 처리하지 않는 변환 실행 시뮬레이션
    ddoc_transform(
        input_path=INPUT_FILE,
        transform_name="image.resize", # ddoc_nlp가 처리하지 않는 변환
        output_path="dummy_output.txt"
    )

    # 4. 정리
    for f in [INPUT_FILE, OUTPUT_TOKENIZE, OUTPUT_NORMALIZE, "dummy_output.txt"]:
        if os.path.exists(f):
             os.remove(f)
