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