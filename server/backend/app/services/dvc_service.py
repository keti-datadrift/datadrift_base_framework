import os
import uuid
import shutil
import subprocess
from pathlib import Path

BASE_DATA_DIR = "dvc_storage/datasets"


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def run_dvc(cmd, cwd="."):
    """DVC 명령 실행 wrapper"""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"DVC error: {cmd}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


# =============================================================
# 1) 업로드 파일 저장만 담당하는 함수
# =============================================================
def save_uploaded_dataset(uploaded_file):
    dataset_id = str(uuid.uuid4())
    dataset_dir = os.path.join(BASE_DATA_DIR, dataset_id)
    ensure_dir(dataset_dir)

    raw_path = os.path.join(dataset_dir, uploaded_file.filename)

    with open(raw_path, "wb") as f:
        shutil.copyfileobj(uploaded_file.file, f)

    return dataset_id, raw_path


# =============================================================
# 2) 단일 파일에 대해 dvc add (csv/txt/img 등)
# =============================================================
def dvc_add_file(file_path: str):
    """
    단일 파일을 위한 DVC add
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    run_dvc(["dvc", "add", file_path])
    return file_path


# =============================================================
# 3) ZIP 데이터셋 처리 (압축 해제 + 분석 + 폴더 dvc add)
# =============================================================
def process_zip_dataset(dataset_id: str, zip_path: str):
    """
    ZIP 파일을 처리:
      1) zip_resolver를 통해 압축 해제 + 정리 + 평탄화
      2) ZIP 구조 분석 결과 반환
    
    Note: 
      - 압축 해제, 불필요한 파일 제거(__MACOSX, .DS_Store 등), 
        이중 구조 평탄화 로직은 zip_resolver._extract_zip에서 처리됨
      - DVC는 현재 사용하지 않음 (2차 작업에서 ddoc 연동 시 처리)
    """
    from app.services.zip_resolver import analyze_zip_dataset

    # ZIP 분석 (내부적으로 압축 해제 + 정리 + 평탄화 수행)
    info = analyze_zip_dataset(zip_path)

    return info


# =============================================================
# 4) DVC 버전 조회 (UI 용)
# =============================================================
def get_dvc_versions(dataset_id: str):
    """
    추후 DVC diff UI를 만들기 위한 placeholder
    """
    try:
        out = run_dvc(["dvc", "list", "."])
        return [{"version": "v1"}]
    except Exception:
        return []