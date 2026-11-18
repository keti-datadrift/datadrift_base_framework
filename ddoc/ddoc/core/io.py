"""
Very small I/O helpers to make builtins work without heavy deps.
"""
from __future__ import annotations
import json
import yaml
from pathlib import Path
from typing import Any, Dict

def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def write_text(path: str, content: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")

def write_json(path: str, obj: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def read_yaml_file(path: str) -> Dict[str, Any]:
    """Read YAML file and return as dictionary"""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def write_yaml_file(path: str, data: Dict[str, Any]) -> None:
    """Write dictionary to YAML file"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)