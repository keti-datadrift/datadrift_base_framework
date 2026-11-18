import subprocess
import os
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List
import networkx as nx

from rich import print
from ddoc.plugins.hookspecs import hookimpl
from ddoc.utils import read_yaml_file, write_yaml_file, get_dvc_status


class CoreOpsPlugin:
    """
    ddoc의 핵심 명령어 실행 엔진입니다.
    Git, DVC, Python 명령어 실행과 기본 유틸리티 기능을 제공합니다.
    비즈니스 로직은 각 서비스(DatasetService, ExperimentService, MetadataService)에 위임합니다.
    """
    def __init__(self, project_root: str = "."):
        # 기본 설정
        self.app_id = "ddoc" 
        self.project_root = Path(project_root)
        
        # 메타데이터 디렉토리만 생성 (실험 디렉토리는 실험 시작 시 생성)
        self.metadata_dir = self.project_root / ".ddoc_metadata"
        self.metadata_dir.mkdir(exist_ok=True)

    # =========================================================================
    # 명령어 래퍼 함수 
    # =========================================================================
    
    def _run_cmd(self, cmd: list[str], log_msg: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """쉘 명령어를 실행하는 헬퍼 함수."""
        print(f"[bold cyan]⚙️ {log_msg}:[/bold cyan] {' '.join(cmd)}")
        try:
            # check=True: 명령 실행 실패 시 CalledProcessError 발생
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                cwd=cwd
            )
            return {"ok": True, "stdout": result.stdout, "stderr": result.stderr}
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip() or e.stdout.strip()
            # 오류 메시지를 포함하여 다시 예외를 발생시켜 호출자에게 전달
            raise Exception(f"{log_msg} 실패: {error_output}")
        except FileNotFoundError:
            raise Exception(f"필요한 명령어({cmd[0]})를 찾을 수 없습니다. (Git 또는 DVC 설치 확인)")

    def _run_git_command(self, args: list[str], description: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Git 명령어 실행 래퍼"""
        return self._run_cmd(["git"] + args, description, cwd)

    def _run_dvc_command(self, args: list[str], description: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """DVC 명령어 실행 래퍼"""
        return self._run_cmd(["dvc"] + args, description, cwd)
    
    def _run_python_command(self, args: list[str], description: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Python 명령어 실행 래퍼"""
        return self._run_cmd(["python"] + args, description, cwd)

    # =========================================================================
    # 헬퍼 함수
    # =========================================================================

    def _update_and_stage_params(self, params: str) -> Optional[Dict[str, Any]]:
        """params.yaml을 업데이트하고 Git에 스테이징하는 공통 로직."""
        try:
            updates = json.loads(params) 
        except json.JSONDecodeError:
            return {"error": "파라미터 업데이트 실패: 'params' 인자가 유효한 JSON 형식이 아닙니다."}
        
        # 🌟 핵심 수정: write_yaml_file 호출을 주석 해제하여 실제로 파일을 업데이트합니다.
        # read_yaml_file로 기존 내용을 읽고 업데이트한 후 저장하는 로직이 필요합니다.
        try:
            # 1. params.yaml 로드 (없으면 빈 딕셔너리로 시작)
            current_params = read_yaml_file("params.yaml") if os.path.exists("params.yaml") else {}
            # 2. 업데이트 병합
            current_params.update(updates)
            # 3. 저장
            write_yaml_file("params.yaml", current_params)
            print(f"[bold green]✔️ Config Update:[/bold green] params.yaml updated with {updates}")
        except Exception as e:
            return {"error": f"params.yaml 파일 쓰기 실패: {e}"}

        # 🌟 Git 스테이징 시 오류 처리 추가
        try:
            self._run_git_command(["add", "params.yaml"], "Git 스테이징: params.yaml")
        except Exception as e:
             # Git 명령 실패 시 오류를 반환
            return {"error": f"params.yaml Git 스테이징 실패: {e}"}
        
        return {"success": True}

    # =========================================================================
    # 유틸리티 함수
    # =========================================================================
    
    def _update_and_stage_params(self, params: str) -> Optional[Dict[str, Any]]:
        """params.yaml을 업데이트하고 Git에 스테이징하는 공통 로직."""
        try:
            # params.yaml 파일 읽기
            current_params = read_yaml_file("params.yaml") if os.path.exists("params.yaml") else {}
            
            # 새로운 파라미터 추가/업데이트
            if params:
                # params가 JSON 문자열인 경우 파싱
                try:
                    import json
                    new_params = json.loads(params)
                    current_params.update(new_params)
                except json.JSONDecodeError:
                    # JSON이 아닌 경우 단순 문자열로 처리
                    current_params['custom_params'] = params
            
            # params.yaml 파일 쓰기
            write_yaml_file("params.yaml", current_params)
            print(f"[bold green]✅ params.yaml 업데이트 완료.[/bold green]")
            
        except Exception as e:
            return {"error": f"params.yaml 파일 쓰기 실패: {e}"}

        # 🌟 Git 스테이징 시 오류 처리 추가
        try:
            self._run_git_command(["add", "params.yaml"], "Git 스테이징: params.yaml")
        except Exception as e:
             # Git 명령 실패 시 오류를 반환
            return {"error": f"params.yaml Git 스테이징 실패: {e}"}
        
        return {"success": True}