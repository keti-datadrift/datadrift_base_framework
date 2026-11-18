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
    return run_dvc(["exp", "show", "-A", "--sort-by", "Created", "--sort-order", "desc", "--json"], project_root)

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
