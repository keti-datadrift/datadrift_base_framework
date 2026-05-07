"""DVC service — Phase 4 (Round-2 Orchestrator Pivot).

Wraps `dvc` CLI commands for the backend. Pre-Phase 4 this module only
exposed ``dvc add``; Phase 4 expands it to ``push`` / ``pull`` /
``status`` / ``remote add`` so multi-site sync of datasets, models, and
keti_veritas-style audit exports goes through one helper layer.

Recommended remote layout (operator-managed; backend does not enforce):

    <DVC_REMOTE_URL>/<DVC_SITE_ID>/
    ├── datasets/      # raw or curated input data per site
    ├── models/        # trained model artifacts per site
    └── audit/         # keti_veritas-style envelope JSON exports

Pipelines (``dvc.yaml`` stages) are intentionally NOT introduced this
round — only sync. The plan calls that out explicitly.
"""
from __future__ import annotations

import logging
import os
import uuid
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DATA_DIR = "dvc_storage/datasets"


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def run_dvc(cmd, cwd: str = ".", *, check: bool = True) -> str:
    """DVC CLI wrapper.

    When ``check`` is True (default) a non-zero exit raises ``RuntimeError``.
    With ``check=False`` the caller receives stdout regardless and is
    responsible for inspecting the result — useful for ``dvc status``
    where dirty trees are non-zero but expected.
    """
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
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


# =============================================================
# 5) Phase 4 — Sync helpers (push / pull / status / remote add)
# =============================================================
def dvc_push(targets: Optional[list[str]] = None, *, remote: Optional[str] = None,
             cwd: str = ".") -> str:
    """Push tracked artifacts to the configured remote.

    ``targets``: optional list of paths or .dvc files to push (defaults to
    everything tracked).
    ``remote``: optional remote name override; falls back to the default
    remote configured by ``dvc remote add -d``.
    """
    cmd = ["dvc", "push"]
    if remote:
        cmd += ["-r", remote]
    if targets:
        cmd += list(targets)
    return run_dvc(cmd, cwd=cwd)


def dvc_pull(targets: Optional[list[str]] = None, *, remote: Optional[str] = None,
             cwd: str = ".") -> str:
    """Pull tracked artifacts from the configured remote (mirror of push)."""
    cmd = ["dvc", "pull"]
    if remote:
        cmd += ["-r", remote]
    if targets:
        cmd += list(targets)
    return run_dvc(cmd, cwd=cwd)


def dvc_status(targets: Optional[list[str]] = None, *, remote: Optional[str] = None,
               cwd: str = ".") -> str:
    """Return ``dvc status`` stdout.

    Uses ``check=False`` because a dirty tree returns non-zero — the
    stdout itself is the useful signal here.
    """
    cmd = ["dvc", "status"]
    if remote:
        cmd += ["-c", "-r", remote]   # -c = compare to remote
    if targets:
        cmd += list(targets)
    return run_dvc(cmd, cwd=cwd, check=False)


def dvc_remote_add(name: str, url: str, *, default: bool = True,
                   cwd: str = ".") -> str:
    """Idempotent ``dvc remote add``. Modify URL if the name already exists."""
    cmd = ["dvc", "remote", "add"]
    if default:
        cmd.append("-d")
    cmd += ["-f", name, url]   # -f → overwrite if remote of same name exists
    return run_dvc(cmd, cwd=cwd)


def dvc_remote_list(cwd: str = ".") -> list[dict[str, str]]:
    """List configured remotes as ``[{name, url}, ...]``."""
    out = run_dvc(["dvc", "remote", "list"], cwd=cwd, check=False)
    items: list[dict[str, str]] = []
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            items.append({"name": parts[0], "url": parts[1]})
    return items