import os
import uuid
import shutil
import subprocess

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
      1) extracted/ 로 압축 해제
      2) 전체 dataset_dir 을 DVC로 관리
      3) ZIP 구조 분석 결과 반환
    """
    import zipfile
    from app.services.zip_resolver import analyze_zip_dataset

    dataset_dir = os.path.dirname(zip_path)
    extracted_dir = os.path.join(dataset_dir, "extracted")
    ensure_dir(extracted_dir)

    # 압축 해제
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extracted_dir)

    # ZIP 구조 분석
    info = analyze_zip_dataset(zip_path)

    # ZIP은 폴더 전체 dvc 관리
    run_dvc(["dvc", "add", dataset_dir])

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