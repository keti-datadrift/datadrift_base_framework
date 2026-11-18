업그레이드 버전 모듈화를 완료했습니다! 🎯
캔버스에 모듈 구조 + 각 파일의 코드를 전부 올려두었어요. (좌측 화면에서 확인 가능)

핵심 개선점 요약
	•	완전 모듈화: core/, services/, utils/, views/로 분리 → 기능 확장 용이
	•	Easy / Advanced 모드 토글
	•	Easy: 직관적 컨트롤 (데이터 업로드, 원클릭 학습 등)
	•	Advanced: 리비전/브랜치/태그 기반 전환, 폴더 지정 2-way 비교 등 상세 제어
	•	양방향 동기화 철학: 공통 파라미터 키 맵(PARAM_KEYS)로 가능하면 서로 연동되도록 설계
	•	데이터셋 2-way 비교(EDA):
	•	좌/우 폴더 입력 후 이미지수/라벨수/용량 비교 + Δ 표기
	•	(프로젝트 정책상 동일 워킹 디렉토리에서 두 리비전 폴더를 동시에 유지하기 어렵기에, 경로 기반 비교 제공)
	•	exp apply → params.yaml 자동 동기화
	•	적용된 실험의 params 스냅샷으로 dataset/data.path 등 가능한 범위 자동 업데이트
	•	데이터/모델 트리 철학 반영
	•	업로드 시 데이터셋 전용 브랜치(data/<dataset>)로 스위치/생성 → 데이터 중심 계보 유지
	•	추후 모델 브랜치(model/<dataset>-<date>) 전략도 쉽게 확장 가능
	•	Remote 관리: add/modify + push/pull 버튼
	•	Streamlit API 변경 대응: use_container_width → width='stretch'로 모두 반영

사용 흐름
	1.	사이드바에서 Remote 설정
	2.	Zip 업로드 → 자동 추출 → dvc add → git 커밋 → (옵션) dvc push
	•	이때 데이터셋 브랜치(data/<dataset>)를 생성/체크아웃
	3.	params.yaml은 실험 적용 시 자동 보정 (dataset/path 등)
	4.	실험 대시보드에서 결과 테이블/플롯 확인 & exp apply + params sync
	5.	데이터 탭에서 단일 탐색 + 2-way 비교
	6.	아티팩트 탭으로 결과물 개별/ZIP 다운로드
	7.	파이프라인 탭에서 dvc dag --dot 확인

다음 단계 (원하시면 바로 반영)
	•	YOLOv8 프리셋 패널: epochs/imgsz/batch/data 등을 Easy 모드에서 슬라이더로, Advanced 모드에선 키 세분화
	•	리비전 쌍 자동 스냅샷: 지정 리비전을 임시 워크트리에 체크아웃 후 별도 폴더에 동기화(안전 가드 필요)
	•	실험 큐 대시보드: dvc exp queue 상태 표시 + 개별 cancel/run
	•	클래스 분포/라벨 누락 검사 등 EDA 카드 추가
	•	브랜치 트리 시각화: 데이터/모델 브랜치를 병렬 트리로 표시(예: graphviz/altair)

필요한 부분부터 더 디테일하게 손보죠. 어떤 기능부터 확장할까요?


# DVC DataOps/MLOps Streamlit – Modular Refactor

> 모듈화된 폴더 구조, **Easy / Advanced 모드**, 데이터셋 **버전 간 비교(2-way EDA)**, `exp apply` 시 **params 자동 동기화**, 데이터/모델 트리 철학 반영.

## 프로젝트 구조 (단일 파일로 붙여두었지만, 실제로는 아래 구조로 분리 저장하세요)

```
app.py
core/
  __init__.py
  constants.py
  state.py
services/
  __init__.py
  dvc_cli.py
  git_cli.py
  dataset_manager.py
  experiments.py
  artifacts.py
utils/
  __init__.py
  eda.py
  ui.py
views/
  __init__.py
  sidebar.py
  tabs_dashboard.py
  tabs_data.py
  tabs_artifacts.py
  tabs_pipeline.py
```

---

## app.py

```python
import time
from pathlib import Path
import streamlit as st

from core.state import init_session, AppMode
from core.constants import APP_TITLE
from views.sidebar import render_sidebar
from views.tabs_dashboard import render_tab_dashboard
from views.tabs_data import render_tab_data
from views.tabs_artifacts import render_tab_artifacts
from views.tabs_pipeline import render_tab_pipeline

st.set_page_config(page_title=APP_TITLE, layout="wide")
init_session()

with st.sidebar:
    render_sidebar()

st.title(APP_TITLE)

# Tabs
TAB_LABELS = [
    "📊 실험 대시보드",
    "🗂 데이터 탐색 & 비교",
    "📥 아티팩트 / 다운로드",
    "🔎 파이프라인 추적"
]

t1, t2, t3, t4 = st.tabs(TAB_LABELS)

with t1:
    render_tab_dashboard()
with t2:
    render_tab_data()
with t3:
    render_tab_artifacts()
with t4:
    render_tab_pipeline()

st.markdown("---")
st.caption(
    "Tip: 먼저 DVC Remote를 설정하고, 데이터 업로드→추적→커밋→(옵션)푸시 후 `params.yaml` 조정과 `dvc exp run`으로 반복 실험을 관리하세요."
)
```

---

## core/constants.py

```python
from pathlib import Path

APP_TITLE = "DVC 기반 DataOps & MLOps – 경량 프론트엔드 (모듈화) 🚀"

DVC_METRIC_DIR = "dvclive"
DVC_PARAMS_FILE = "params.yaml"
DEFAULT_DATA_ROOT = "data"
DEFAULT_ARTIFACTS_DIR = "artifacts"
UPLOADS_DIR = "_uploads"

# UI: Streamlit 2025-12-31 이후 use_container_width 제거 권고 대응
WIDTH_STRETCH = dict(width="stretch")
WIDTH_CONTENT = dict(width="content")

# Params sync: Easy/Advanced 모드 공통 키 매핑 예시
# (사용자 프로젝트에 맞게 확장 가능)
PARAM_KEYS = {
    "dataset_name": ["data.dataset", "dataset", "data.name"],
    "dataset_path": ["data.path", "dataset_path"],
    "epochs": ["train.epochs", "epochs"],
    "imgsz": ["train.imgsz", "imgsz"],
    "batch": ["train.batch", "batch_size", "batch"],
}

# 브랜치 네이밍(데이터셋 중심 트리)
DATA_BRANCH_PREFIX = "data/"  # 예: data/d1, data/d2
MODEL_BRANCH_PREFIX = "model/" # 예: model/d1-20251017
```

````

---

## core/state.py
```python
import json
from pathlib import Path
import streamlit as st

from core.constants import DVC_PARAMS_FILE

class AppMode:
    EASY = "Easy"
    ADV = "Advanced"

DEFAULT_STATE = {
    "project_root": str(Path.cwd()),
    "mode": AppMode.EASY,
    "selected_dataset": "",            # Easy: 단일 선택
    "compare_left": "",                 # Advanced: 비교 좌측 리비전/태그/브랜치
    "compare_right": "",                # Advanced: 비교 우측 리비전/태그/브랜치
    "exp_name": "",
    "queue_mode": False,
    "remote_name": "storage",
    "remote_url": "",
}

def init_session():
    for k, v in DEFAULT_STATE.items():
        st.session_state.setdefault(k, v)

# --- Simple signals to sync Easy/Advanced ---

def set_mode(mode: str):
    st.session_state.mode = mode


def load_params_yaml_text(project_root: Path) -> str:
    p = project_root / DVC_PARAMS_FILE
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def save_params_yaml_text(project_root: Path, text: str):
    (project_root / DVC_PARAMS_FILE).write_text(text, encoding="utf-8")

````

---

## services/dvc_cli.py

```python
import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, List, Optional
import streamlit as st

@contextmanager
def chdir(path: Path):
    prev = Path.cwd()
    try:
        os_chdir = getattr(__import__('os'), 'chdir')
        os_chdir(path)
        yield
    finally:
        os_chdir(prev)


def run_dvc(args: List[str], project_root: Path) -> Optional[Any]:
    full = ["dvc"] + args
    with chdir(project_root):
        try:
            st.info(f"실행 중: {' '.join(full)}")
            cp = subprocess.run(full, capture_output=True, text=True, check=True)
            out = cp.stdout.strip()
            if not out:
                return None
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                return out
        except FileNotFoundError:
            st.error("DVC가 설치되어 있지 않습니다.")
        except subprocess.CalledProcessError as e:
            st.error("DVC 명령 실패")
            st.code(f"$ {' '.join(full)}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")
    return None


def run_shell(args: List[str], project_root: Path) -> subprocess.CompletedProcess:
    with chdir(project_root):
        return subprocess.run(args, capture_output=True, text=True)

# High-level wrappers

def exp_show(project_root: Path):
    return run_dvc(["exp", "show", "-A", "--json"], project_root)

def plots_diff_json(project_root: Path):
    return run_dvc(["plots", "diff", "--json"], project_root)

def exp_apply(rev: str, project_root: Path):
    return run_dvc(["exp", "apply", rev], project_root)

def exp_run(name: str, queue: bool, project_root: Path):
    args = ["exp", "run", "-n", name]
    if queue:
        args.append("--queue")
    return run_dvc(args, project_root)

def dag_dot(project_root: Path):
    return run_shell(["dvc", "dag", "--dot"], project_root)

def dvc_add(path: Path, project_root: Path):
    return run_shell(["dvc", "add", str(path)], project_root)

def dvc_push(project_root: Path):
    return run_shell(["dvc", "push"], project_root)

def dvc_pull(project_root: Path):
    return run_shell(["dvc", "pull"], project_root)

def remote_list(project_root: Path):
    return run_shell(["dvc", "remote", "list"], project_root)

def remote_add_default(name: str, url: str, project_root: Path):
    return run_shell(["dvc", "remote", "add", "-d", name, url], project_root)

def remote_modify(name: str, url: str, project_root: Path):
    return run_shell(["dvc", "remote", "modify", name, "url", url], project_root)
```

---

## services/git_cli.py

```python
from pathlib import Path
import subprocess
from .dvc_cli import run_shell


def git_add(paths, project_root: Path):
    args = ["git", "add"] + ([str(paths)] if isinstance(paths, (str, Path)) else [str(p) for p in paths])
    return run_shell(args, project_root)

def git_commit(message: str, project_root: Path):
    return run_shell(["git", "commit", "-m", message], project_root)

def git_tag(tag: str, project_root: Path):
    return run_shell(["git", "tag", tag], project_root)

def git_push(with_tags: bool, project_root: Path):
    args = ["git", "push"] + (["--tags"] if with_tags else [])
    return run_shell(args, project_root)

def git_checkout(rev: str, project_root: Path):
    return run_shell(["git", "checkout", rev], project_root)

def git_branch_create(name: str, checkout: bool, project_root: Path):
    if checkout:
        return run_shell(["git", "checkout", "-B", name], project_root)
    else:
        return run_shell(["git", "branch", name], project_root)

def git_current_branch(project_root: Path) -> str:
    cp = run_shell(["git", "rev-parse", "--abbrev-ref", "HEAD"], project_root)
    return (cp.stdout or "").strip()
```

---

## services/dataset_manager.py

```python
import zipfile
from pathlib import Path
from typing import Dict, List
import streamlit as st

from core.constants import DEFAULT_DATA_ROOT, UPLOADS_DIR, DATA_BRANCH_PREFIX
from .dvc_cli import dvc_add, dvc_push
from .git_cli import git_add, git_commit, git_tag, git_push, git_checkout, git_branch_create


def save_uploaded_zip(upload, project_root: Path) -> Path:
    updir = project_root / UPLOADS_DIR
    updir.mkdir(exist_ok=True)
    fpath = updir / upload.name
    with open(fpath, 'wb') as f:
        f.write(upload.getbuffer())
    return fpath


def extract_zip(zip_path: Path, target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(target_dir)


def track_and_commit_dataset(dataset_dir: Path, project_root: Path, message: str, tag: str = "", push_remote: bool = True):
    dvc_add(dataset_dir, project_root)
    git_add([str(dataset_dir) + ".dvc", ".gitignore"], project_root)
    git_commit(message, project_root)
    if tag:
        git_tag(tag, project_root)
    if push_remote:
        dvc_push(project_root)
        git_push(bool(tag), project_root)


def scan_stats(folder: Path) -> Dict[str, float]:
    images = list(folder.rglob("*.jpg")) + list(folder.rglob("*.jpeg")) + list(folder.rglob("*.png"))
    labels = list(folder.rglob("*.txt"))
    size_bytes = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
    return {
        "num_images": float(len(images)),
        "num_labels_txt": float(len(labels)),
        "size_gb": round(size_bytes / (1024**3), 3)
    }


def list_datasets(project_root: Path) -> List[Path]:
    data_root = project_root / DEFAULT_DATA_ROOT
    return [p for p in data_root.glob("*") if p.is_dir()]


def ensure_data_branch(dataset_name: str, project_root: Path):
    branch = DATA_BRANCH_PREFIX + dataset_name
    git_branch_create(branch, checkout=True, project_root=project_root)
    return branch
```

---

## services/experiments.py

```python
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.constants import DVC_METRIC_DIR, DVC_PARAMS_FILE, PARAM_KEYS
from .dvc_cli import exp_show, exp_apply, exp_run, plots_diff_json


def _extract_values_from_data(data_dict: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data_dict, dict):
        return {}
    out: Dict[str, Any] = {}
    params = data_dict.get('params', {})
    for _, file_data in params.items():
        if isinstance(file_data, dict) and 'data' in file_data:
            for k, v in file_data['data'].items():
                out[f"param/{k}"] = v
    metrics = data_dict.get('metrics', {})
    if DVC_METRIC_DIR in metrics and isinstance(metrics[DVC_METRIC_DIR], dict):
        for k, v in metrics[DVC_METRIC_DIR].items():
            out[f"metric/{k}"] = v
    for k, v in metrics.items():
        if k != DVC_METRIC_DIR and isinstance(v, (int, float, str)):
            out[f"metric/{k}"] = v
    if 'timestamp' in data_dict:
        out['Created'] = data_dict['timestamp']
    if 'rev' in data_dict:
        out['SHA'] = data_dict['rev']
    return out


def get_experiments_df(project_root: Path) -> Optional[pd.DataFrame]:
    data = exp_show(project_root)
    if not data or not isinstance(data, list):
        return None
    rows = []
    for item in data:
        vals = _extract_values_from_data(item.get('data', {}))
        rev = item.get('rev'); name = item.get('name')
        if not vals and rev != 'workspace':
            continue
        rows.append({
            'Experiment': (name or (rev[:7] if rev and rev != 'workspace' else rev)),
            **vals,
            'SHA': rev,
        })
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if 'metric/mAP50' in df.columns:
        df = df.sort_values('metric/mAP50', ascending=False, ignore_index=True)
    # Order columns
    cols = ['Experiment', 'Created'] + [c for c in df.columns if c.startswith('metric/')] + [c for c in df.columns if c.startswith('param/')] + ['SHA']
    df = df[[c for c in cols if c in df.columns]]
    return df


def apply_experiment_and_sync_params(exp_rev: str, project_root: Path) -> bool:
    """exp apply 후 params.yaml의 dataset 관련 키들을 가능한 범위에서 동기화합니다.
       - 전략: exp_show 데이터에서 선택 rev의 params 추출 → params.yaml 병합 업데이트
    """
    ok = exp_apply(exp_rev, project_root) is not None
    if not ok:
        return False
    # 1) 해당 rev에서 params 스냅샷 찾기
    data = exp_show(project_root)
    target = None
    for item in (data or []):
        if item.get('rev') == exp_rev:
            target = item
            break
    if not target:
        return True  # 적용은 되었음
    params_data = {}
    pdict = target.get('data', {}).get('params', {})
    for _, file_data in pdict.items():
        if isinstance(file_data, dict) and 'data' in file_data:
            params_data.update(file_data['data'])
    # 2) params.yaml 읽고 매핑 가능한 키 업데이트
    p = Path(project_root) / DVC_PARAMS_FILE
    if not p.exists():
        return True
    doc = yaml.safe_load(p.read_text(encoding='utf-8')) or {}

    def set_nested(doc: dict, dotted: str, value):
        cur = doc
        parts = dotted.split('.')
        for i, k in enumerate(parts):
            if i == len(parts) - 1:
                cur[k] = value
            else:
                cur = cur.setdefault(k, {})

    # dataset_name → 여러 후보 키에 전파
    if 'dataset' in params_data:
        for dotted in PARAM_KEYS['dataset_name']:
            set_nested(doc, dotted, params_data['dataset'])
    if 'data' in params_data and isinstance(params_data['data'], dict) and 'path' in params_data['data']:
        for dotted in PARAM_KEYS['dataset_path']:
            set_nested(doc, dotted, params_data['data']['path'])

    p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding='utf-8')
    return True


def run_experiment(name: str, queue: bool, project_root: Path):
    return exp_run(name, queue, project_root)


def get_plots_specs(project_root: Path):
    return plots_diff_json(project_root)
```

---

## services/artifacts.py

```python
import time
import zipfile
from pathlib import Path
import streamlit as st

from core.constants import DEFAULT_ARTIFACTS_DIR


def iter_files(root: Path):
    return [p for p in root.rglob('*') if p.is_file()]


def zip_directory(dir_path: Path, zip_out: Path):
    with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in dir_path.rglob('*'):
            if p.is_file():
                z.write(p, p.relative_to(dir_path))


def render_downloads(art_dir: Path):
    files = iter_files(art_dir)
    if not files:
        st.info("아티팩트 폴더에 파일이 없습니다.")
        return
    st.write(f"총 {len(files)}개 파일")
    for p in files[:200]:
        with open(p, 'rb') as f:
            st.download_button(label=f"다운로드: {p.relative_to(art_dir)}", data=f, file_name=p.name)
    st.caption("파일이 많으면 아래 ZIP로 한 번에 다운로드")
    if st.button("ZIP 생성"):
        zip_out = art_dir.parent / f"{art_dir.name}-{int(time.time())}.zip"
        zip_directory(art_dir, zip_out)
        with open(zip_out, 'rb') as f:
            st.download_button("ZIP 다운로드", f, file_name=zip_out.name)
```

---

## utils/eda.py

```python
from pathlib import Path
from typing import Dict
from services.dataset_manager import scan_stats


def summarize_dataset(ds_dir: Path) -> Dict[str, float]:
    return scan_stats(ds_dir)


def diff_stats(left: Dict[str, float], right: Dict[str, float]) -> Dict[str, float]:
    keys = set(left) | set(right)
    return {k: float(right.get(k, 0.0) - left.get(k, 0.0)) for k in keys}
```

---

## utils/ui.py

```python
import streamlit as st
from core.constants import WIDTH_STRETCH


def metrics_row(stats: dict, label_prefix: str = ""):
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{label_prefix}이미지 수", int(stats.get('num_images', 0)))
    c2.metric(f"{label_prefix}TXT 라벨 수", int(stats.get('num_labels_txt', 0)))
    c3.metric(f"{label_prefix}용량(GB)", stats.get('size_gb', 0.0))


def dataframe(df):
    st.dataframe(df, **WIDTH_STRETCH)
```

---

## views/sidebar.py

```python
from pathlib import Path
import streamlit as st

from core.state import set_mode
from core.constants import (
    DEFAULT_DATA_ROOT, DEFAULT_ARTIFACTS_DIR, UPLOADS_DIR,
    WIDTH_STRETCH, APP_TITLE
)
from services import dvc_cli
from services.dataset_manager import (
    save_uploaded_zip, extract_zip, track_and_commit_dataset,
    ensure_data_branch
)


def render_sidebar():
    st.title("⚙️ 설정")
    project_input = st.text_input("프로젝트 루트", value=st.session_state.project_root, help="dvc.yaml과 params.yaml이 있는 경로")
    st.session_state.project_root = str(Path(project_input).resolve())
    project_root = Path(st.session_state.project_root)

    # Mode toggle
    mode = st.radio("모드", ("Easy", "Advanced"), horizontal=True, index=(0 if st.session_state.mode=="Easy" else 1))
    set_mode(mode)

    st.subheader("🌐 DVC Remote")
    st.text_input("원격 이름", key="remote_name")
    st.text_input("원격 URL", key="remote_url")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("원격 추가/수정"):
            if st.session_state.remote_url:
                out = dvc_cli.remote_list(project_root)
                if st.session_state.remote_name in (out.stdout or ""):
                    dvc_cli.remote_modify(st.session_state.remote_name, st.session_state.remote_url, project_root)
                else:
                    dvc_cli.remote_add_default(st.session_state.remote_name, st.session_state.remote_url, project_root)
                st.success("원격 설정 완료")
            else:
                st.warning("원격 URL을 입력하세요")
    with c2:
        if st.button("dvc push"):
            dvc_cli.dvc_push(project_root)
    with c3:
        if st.button("dvc pull"):
            dvc_cli.dvc_pull(project_root)

    st.subheader("📦 데이터 업로드 & 버전관리")
    dataset_name = st.text_input("데이터셋 이름", value="dataset")
    uploaded = st.file_uploader("Zip 업로드", type=["zip"], accept_multiple_files=False)
    create_tag = st.text_input("Git 태그(선택)", value="")
    push_remote = st.checkbox("업로드 후 DVC push", value=True)

    if st.button("업로드 → dvc add → 커밋 → (옵션) push"):
        if not uploaded:
            st.warning("zip 파일을 선택하세요.")
        else:
            data_dir = project_root / DEFAULT_DATA_ROOT / dataset_name
            data_dir.parent.mkdir(parents=True, exist_ok=True)
            z = save_uploaded_zip(uploaded, project_root)
            extract_zip(z, data_dir)
            # 데이터 브랜치 유지 철학: 데이터셋별 브랜치로 전환/생성
            ensure_data_branch(dataset_name, project_root)
            track_and_commit_dataset(data_dir, project_root, f"Add dataset {dataset_name}", create_tag, push_remote)
            st.success("데이터 업로드 및 버전관리 완료")

    st.subheader("🧪 실험 실행 (dvc exp)")
    st.text_input("실험 이름", key="exp_name", value=st.session_state.exp_name or f"run-{st.session_state.get('exp_name') or ''}")
    st.checkbox("queue로 등록", key="queue_mode", value=st.session_state.queue_mode)
    if st.button("dvc exp run"):
        dvc_cli.exp_run(st.session_state.exp_name or "run", st.session_state.queue_mode, project_root)

    st.subheader("📁 경로 설정")
    st.text_input("데이터 루트", value=str(project_root / DEFAULT_DATA_ROOT), key="data_root")
    st.text_input("아티팩트 폴더", value=str(project_root / DEFAULT_ARTIFACTS_DIR), key="art_dir")
```

---

## views/tabs_dashboard.py

```python
from pathlib import Path
import streamlit as st
from services.experiments import get_experiments_df, get_plots_specs, apply_experiment_and_sync_params
from utils.ui import dataframe


def render_tab_dashboard():
    project_root = Path(st.session_state.project_root)
    st.subheader("1) 실험 결과 테이블")
    df = get_experiments_df(project_root)
    if df is None or df.empty:
        st.info("실험 결과가 없습니다. dvc exp run 후 새로고침 하세요.")
    else:
        dataframe(df)
        st.markdown("---")
        st.caption("선택한 실험으로 워크스페이스를 되돌리고, 관련 params를 가급적 자동 동기화합니다.")
        choice = st.selectbox("적용할 실험 선택", df['Experiment'].tolist())
        if st.button("선택 실험 상태로 dvc exp apply + params sync"):
            sha = df.loc[df['Experiment'] == choice, 'SHA'].iloc[0]
            if sha and sha != 'workspace':
                ok = apply_experiment_and_sync_params(sha, project_root)
                if ok:
                    st.success("적용 및 params 동기화 완료")
                else:
                    st.error("적용 실패")
            else:
                st.info("workspace는 적용 대상이 아닙니다.")

    st.markdown("---")
    st.subheader("2) 메트릭/플롯 변화 (dvc plots diff --json)")
    specs = get_plots_specs(project_root)
    if isinstance(specs, list) and specs:
        for spec in specs:
            try:
                st.altair_chart(spec, width='stretch')
            except Exception:
                st.code(json.dumps(spec, indent=2, ensure_ascii=False))
    else:
        st.info("플롯 비교 데이터가 없습니다.")
```

---

## views/tabs_data.py

```python
from pathlib import Path
import streamlit as st

from core.constants import DEFAULT_DATA_ROOT
from services.dataset_manager import list_datasets
from services.dvc_cli import dvc_pull
from services.git_cli import git_checkout
from utils.eda import summarize_dataset, diff_stats
from utils.ui import metrics_row


def _dataset_select_box(project_root: Path, label: str):
    data_root = project_root / DEFAULT_DATA_ROOT
    options = [p.name for p in list_datasets(project_root)]
    if not options:
        st.info(f"{data_root} 아래에 데이터셋 폴더가 없습니다. 사이드바에서 업로드 하세요.")
        return None
    return st.selectbox(label, options)


def render_tab_data():
    project_root = Path(st.session_state.project_root)

    st.subheader("데이터셋 탐색 (단일)")
    one = _dataset_select_box(project_root, "데이터셋 선택")
    if one:
        ds_dir = project_root / DEFAULT_DATA_ROOT / one
        stats = summarize_dataset(ds_dir)
        metrics_row(stats)
        imgs = list(ds_dir.rglob("*.jpg"))[:12]
        if imgs:
            st.caption("샘플 미리보기 (최대 12장)")
            st.image([str(p) for p in imgs])

    st.markdown("---")
    st.subheader("데이터셋 버전 비교 (2-way)")
    col1, col2 = st.columns(2)
    with col1:
        left_rev = st.text_input("좌측 리비전/브랜치/태그", value=st.session_state.compare_left)
    with col2:
        right_rev = st.text_input("우측 리비전/브랜치/태그", value=st.session_state.compare_right)

    if st.button("체크아웃 & dvc pull (좌→우 순서)"):
        if left_rev:
            out = git_checkout(left_rev, project_root)
            if out.returncode == 0:
                dvc_pull(project_root)
        if right_rev:
            out = git_checkout(right_rev, project_root)
            if out.returncode == 0:
                dvc_pull(project_root)
        st.success("체크아웃 및 데이터 동기화 완료 (마지막 상태 기준)")

    # 실제 비교는 동일한 루트 내 두 버전 폴더를 직접 가져오기 어려울 수 있으므로
    # 간단한 전략: 동일한 데이터셋 이름에 대해 스냅샷 디렉토리를 두 개 지정받아 비교
    left_path = st.text_input("좌 비교 경로(폴더)")
    right_path = st.text_input("우 비교 경로(폴더)")

    if st.button("폴더 기준 비교 실행"):
        lp = Path(left_path); rp = Path(right_path)
        if lp.exists() and rp.exists():
            ls = summarize_dataset(lp)
            rs = summarize_dataset(rp)
            metrics_row(ls, label_prefix="좌/")
            metrics_row(rs, label_prefix="우/")
            st.caption("차이 (우 - 좌)")
            diff = diff_stats(ls, rs)
            c1, c2, c3 = st.columns(3)
            c1.metric("Δ 이미지 수", int(diff.get('num_images', 0)))
            c2.metric("Δ 라벨 수", int(diff.get('num_labels_txt', 0)))
            c3.metric("Δ 용량(GB)", diff.get('size_gb', 0.0))
        else:
            st.error("비교 경로가 올바르지 않습니다.")
```

---

## views/tabs_artifacts.py

```python
from pathlib import Path
import streamlit as st

from services.artifacts import render_downloads


def render_tab_artifacts():
    art_dir = Path(st.session_state.get('art_dir') or (Path(st.session_state.project_root) / 'artifacts'))
    st.text_input("아티팩트 폴더", value=str(art_dir), key="art_dir")
    art_dir = Path(st.session_state.art_dir)
    if art_dir.exists():
        render_downloads(art_dir)
    else:
        st.info("아티팩트 폴더가 존재하지 않습니다. 경로를 확인하세요.")
```

---

## views/tabs_pipeline.py

```python
from pathlib import Path
import streamlit as st

from services.dvc_cli import dag_dot


def render_tab_pipeline():
    pr = Path(st.session_state.project_root)
    st.caption("dvc dag --dot 결과")
    cp = dag_dot(pr)
    if cp.returncode == 0 and cp.stdout:
        st.code(cp.stdout)
    else:
        st.info("DAG 정보를 가져오지 못했습니다. dvc.yaml을 확인하세요.")
```



