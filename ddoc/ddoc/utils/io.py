import yaml
import subprocess
import os
from typing import Any, Dict

def read_yaml_file(filepath: str) -> Dict[str, Any]:
    """
    Reads a YAML file and returns its content as a dictionary.
    
    Args:
        filepath: The path to the YAML file.

    Returns:
        The content of the YAML file as a dictionary, or an empty dict if the file 
        does not exist.
    """
    if not os.path.exists(filepath):
        # 파일이 존재하지 않으면 빈 딕셔너리 반환
        return {}
        
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            # 안전하게 YAML을 로드합니다. 내용이 비어있을 경우 {}를 반환합니다.
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise Exception(f"YAML 파일을 읽는 중 오류 발생 ({filepath}): {e}")


def _recursive_update(target: Dict[str, Any], updates: Dict[str, Any]) -> None:
    """
    Recursively updates a dictionary (target) with another dictionary (updates).
    Used to safely update nested configurations like params.yaml.
    """
    for key, value in updates.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            # 대상과 업데이트 모두 딕셔너리인 경우 재귀적으로 업데이트
            _recursive_update(target[key], value)
        else:
            # 그렇지 않은 경우 값을 직접 할당 (존재하지 않으면 생성, 존재하면 덮어쓰기)
            target[key] = value

def write_yaml_file(filepath: str, updates: Dict[str, Any]) -> None:
    """
    Reads a YAML file, merges updates into the existing content (if any), and 
    writes the resulting content back. If the file does not exist, it creates a new file.

    Args:
        filepath: The path to the YAML file (e.g., 'params.yaml').
        updates: A dictionary containing the new key-value pairs to merge.
    """
    # 1. 기존 내용을 읽어오거나 (파일이 있으면), 빈 딕셔너리부터 시작합니다.
    current_content = read_yaml_file(filepath)
    
    # 2. 새 업데이트를 기존 내용에 재귀적으로 병합합니다.
    _recursive_update(current_content, updates)

    # 3. 업데이트된 내용을 파일에 다시 씁니다.
    with open(filepath, 'w', encoding='utf-8') as f:
        # YAML 포맷을 유지하기 위해 sort_keys=False 및 default_flow_style=False 사용
        yaml.safe_dump(current_content, f, sort_keys=False, default_flow_style=False)


def get_dvc_status() -> str:
    """
    Runs 'dvc status' command and returns its output.
    Raises an exception if the command fails or DVC is not found.
    """
    try:
        # DVC 명령어가 설치되어 있고 DVC 저장소가 초기화되었다고 가정합니다.
        result = subprocess.run(
            ["dvc", "status"], 
            check=True, 
            capture_output=True, 
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # DVC 명령 실행 실패 시 에러 반환
        raise Exception(f"'dvc status' 실행 실패: {e.stderr.strip()}")
    except FileNotFoundError:
        # DVC 명령어를 찾을 수 없는 경우
        raise Exception("DVC 명령어를 찾을 수 없습니다. DVC가 설치되어 있는지 확인해주세요.")
