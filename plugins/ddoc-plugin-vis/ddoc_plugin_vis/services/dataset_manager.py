
# ================================
# File: services/dataset_manager.py
# ================================
"""services/dataset_manager.py
Extended, extensible data manager for mixed-modality datasets & common CV formats.
- Safe image verification to avoid PIL.UnidentifiedImageError
- Nested directory support (any depth via rglob)
- Modality-aware stats (image, text, audio, video, csv/timeseries, xml, json, other)
- Dataset format hints (YOLO, Pascal VOC, COCO)
- Class distribution (YOLO/VOC/COCO) with optional label names
- Lightweight media probing via ffprobe (if available)
- CSV preview helpers
"""
from __future__ import annotations

import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Any

import streamlit as st

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

from core.constants import DEFAULT_DATA_ROOT, UPLOADS_DIR
from services.dvc_cli import dvc_add, dvc_push
from services.git_cli import git_add, git_commit, git_tag, git_push, git_branch_create

# -------------------------------
# Enums / Typing
# -------------------------------
class FileType(Enum):
    IMAGE = auto()
    TEXT = auto()
    AUDIO = auto()
    VIDEO = auto()
    CSV = auto()         # timeseries/tabular
    XML = auto()
    JSON = auto()
    OTHER = auto()


class DatasetFormat(Enum):
    UNKNOWN = auto()
    YOLO = auto()        # images/* + labels/*.txt (cx cy w h)
    PASCAL_VOC = auto()  # Annotations/*.xml + JPEGImages/*.jpg
    COCO = auto()        # images/*.jpg + annotations/*.json


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
TEXT_EXTS  = {".txt", ".md", ".log"}
CSV_EXTS   = {".csv"}
XML_EXTS   = {".xml"}
JSON_EXTS  = {".json"}

# -------------------------------
# Upload helpers (unchanged API)
# -------------------------------
def save_uploaded_zip(upload, project_root: Path) -> Path:
    updir = project_root / UPLOADS_DIR
    updir.mkdir(exist_ok=True, parents=True)
    fpath = updir / upload.name
    with open(fpath, 'wb') as f:
        f.write(upload.getbuffer())
    return fpath


def extract_zip(zip_path: Path, target_dir: Path) -> None:
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


def ensure_data_branch(dataset_name: str, project_root: Path, prefix: str = "data/") -> str:
    branch = prefix + dataset_name
    git_branch_create(branch, checkout=True, project_root=project_root)
    return branch

# -------------------------------
# Core scanning & validation
# -------------------------------

def _classify(path: Path) -> FileType:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return FileType.IMAGE
    if ext in AUDIO_EXTS:
        return FileType.AUDIO
    if ext in VIDEO_EXTS:
        return FileType.VIDEO
    if ext in CSV_EXTS:
        return FileType.CSV
    if ext in XML_EXTS:
        return FileType.XML
    if ext in JSON_EXTS:
        return FileType.JSON
    if ext in TEXT_EXTS:
        return FileType.TEXT
    return FileType.OTHER


def _iter_files(root: Path) -> Iterable[Path]:
    return (p for p in root.rglob("*") if p.is_file())


def _is_valid_image(path: Path) -> bool:
    if _classify(path) is not FileType.IMAGE:
        return False
    if not PIL_AVAILABLE:
        return True
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def enumerate_valid_images(root: Path, limit: Optional[int] = None) -> List[Path]:
    valid: List[Path] = []
    for p in _iter_files(root):
        if _is_valid_image(p):
            valid.append(p)
            if limit is not None and len(valid) >= limit:
                break
    return valid

# -------------------------------
# Media probing (ffprobe if available)
# -------------------------------

def _ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def probe_media_summary(root: Path) -> Dict[str, Any]:
    out = {"audio_count": 0, "video_count": 0, "audio_seconds": 0.0, "video_seconds": 0.0}
    if not _ffprobe_available():
        for p in _iter_files(root):
            t = _classify(p)
            if t is FileType.AUDIO:
                out["audio_count"] += 1
            elif t is FileType.VIDEO:
                out["video_count"] += 1
        return out

    import subprocess, json as _json
    for p in _iter_files(root):
        t = _classify(p)
        if t not in {FileType.AUDIO, FileType.VIDEO}:
            continue
        try:
            cmd = [
                "ffprobe", "-v", "error", "-print_format", "json",
                "-show_entries", "format=duration", str(p)
            ]
            cp = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = _json.loads(cp.stdout or '{}')
            dur = float(data.get('format', {}).get('duration', 0.0) or 0.0)
            if t is FileType.AUDIO:
                out["audio_count"] += 1
                out["audio_seconds"] += dur
            else:
                out["video_count"] += 1
                out["video_seconds"] += dur
        except Exception:
            if t is FileType.AUDIO:
                out["audio_count"] += 1
            else:
                out["video_count"] += 1
    out["audio_seconds"] = round(out["audio_seconds"], 2)
    out["video_seconds"] = round(out["video_seconds"], 2)
    return out

# -------------------------------
# Dataset statistics & format detection
# -------------------------------
@dataclass
class DatasetStats:
    num_images: int = 0
    num_audio: int = 0
    num_video: int = 0
    num_text: int = 0
    num_csv: int = 0
    num_xml: int = 0
    num_json: int = 0
    num_other: int = 0
    size_gb: float = 0.0
    format_hint: 'DatasetFormat' = None  # type: ignore


def scan_stats(folder: Path) -> DatasetStats:
    total_bytes = 0
    counts = {t: 0 for t in FileType}
    for p in _iter_files(folder):
        try:
            total_bytes += p.stat().st_size
        except Exception:
            pass
        counts[_classify(p)] += 1
    fmt = _detect_format(folder)
    return DatasetStats(
        num_images=counts[FileType.IMAGE],
        num_audio=counts[FileType.AUDIO],
        num_video=counts[FileType.VIDEO],
        num_text=counts[FileType.TEXT],
        num_csv=counts[FileType.CSV],
        num_xml=counts[FileType.XML],
        num_json=counts[FileType.JSON],
        num_other=counts[FileType.OTHER],
        size_gb=round(total_bytes / (1024 ** 3), 3),
        format_hint=fmt,
    )


def _detect_format(root: Path) -> 'DatasetFormat':
    labels = list(root.rglob("labels/*.txt"))
    images = [p for p in root.rglob("images/*") if p.suffix.lower() in IMAGE_EXTS]
    if labels and images:
        return DatasetFormat.YOLO
    if list(root.rglob("Annotations/*.xml")) and list(root.rglob("JPEGImages/*")):
        return DatasetFormat.PASCAL_VOC
    if list(root.rglob("annotations/*.json")) and images:
        return DatasetFormat.COCO
    return DatasetFormat.UNKNOWN

# -------------------------------
# Public API for dataset browsing
# -------------------------------

def summarize_dataset(ds_dir: Path) -> Dict[str, Any]:
    stats = scan_stats(ds_dir)
    media = probe_media_summary(ds_dir)
    return {
        "num_images": float(stats.num_images),
        "num_audio": float(stats.num_audio),
        "num_video": float(stats.num_video),
        "num_text": float(stats.num_text),
        "num_csv": float(stats.num_csv),
        "num_xml": float(stats.num_xml),
        "num_json": float(stats.num_json),
        "num_other": float(stats.num_other),
        "size_gb": stats.size_gb,
        "format": stats.format_hint.name if stats.format_hint else 'UNKNOWN',
        **media,
    }


def list_datasets(project_root: Path) -> List[Path]:
    data_root = project_root / DEFAULT_DATA_ROOT
    if not data_root.exists():
        return []
    return [p for p in data_root.glob("*") if p.is_dir()]


def preview_samples(ds_dir: Path, limit: int = 12) -> List[Path]:
    return enumerate_valid_images(ds_dir, limit=limit)

# -------------------------------
# Class distributions (YOLO / VOC / COCO)
# -------------------------------

def yolo_class_counts(root: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for txt in root.rglob("labels/*.txt"):
        try:
            if txt.stat().st_size == 0:
                continue
            for line in txt.read_text(encoding='utf-8', errors='ignore').splitlines():
                parts = line.strip().split()
                if not parts:
                    continue
                try:
                    cls = int(float(parts[0]))
                except Exception:
                    continue
                counts[str(cls)] = counts.get(str(cls), 0) + 1
        except Exception:
            continue
    data_yaml = next(root.rglob("data.yaml"), None)
    if data_yaml:
        try:
            import yaml
            doc = yaml.safe_load(data_yaml.read_text(encoding='utf-8')) or {}
            names = doc.get('names')
            if isinstance(names, list):
                counts = { (names[int(k)] if int(k) < len(names) else k): v for k, v in counts.items() }
        except Exception:
            pass
    return counts


def voc_class_counts(root: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for xmlp in root.rglob("Annotations/*.xml"):
        try:
            tree = ET.parse(xmlp)
            for obj in tree.getroot().iterfind('object'):
                name_el = obj.find('name')
                if name_el is not None and name_el.text:
                    k = name_el.text.strip()
                    counts[k] = counts.get(k, 0) + 1
        except Exception:
            continue
    return counts


def coco_class_counts(root: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    ann_json = None
    for cand in root.rglob("annotations/*.json"):
        ann_json = cand
        break
    if not ann_json:
        return counts
    try:
        data = json.loads(ann_json.read_text(encoding='utf-8'))
        cat_map = {c['id']: c.get('name', str(c['id'])) for c in data.get('categories', [])}
        for ann in data.get('annotations', []):
            cid = ann.get('category_id')
            name = cat_map.get(cid, str(cid))
            counts[name] = counts.get(name, 0) + 1
    except Exception:
        pass
    return counts


def class_distribution(root: Path, fmt: 'DatasetFormat' | None = None) -> Dict[str, int]:
    if fmt is None:
        fmt = _detect_format(root)
    if fmt is DatasetFormat.YOLO:
        return yolo_class_counts(root)
    if fmt is DatasetFormat.PASCAL_VOC:
        return voc_class_counts(root)
    if fmt is DatasetFormat.COCO:
        return coco_class_counts(root)
    return {}

# -------------------------------
# CSV / timeseries preview
# -------------------------------

def first_csv_preview(root: Path, max_rows: int = 1000):
    try:
        import pandas as pd
    except Exception:
        return None
    csvs = list(root.rglob("*.csv"))
    if not csvs:
        return None
    f = csvs[0]
    try:
        df = pd.read_csv(f, nrows=max_rows)
        return str(f), df
    except Exception:
        return None

# -------------------------------
# Simple comparisons for EDA
# -------------------------------

def diff_stats(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, float]:
    num_keys = {k for k, v in left.items() if isinstance(v, (int, float))} | {k for k, v in right.items() if isinstance(v, (int, float))}
    out: Dict[str, float] = {}
    for k in sorted(num_keys):
        out[k] = float((right.get(k, 0.0) or 0.0) - (left.get(k, 0.0) or 0.0))
    return out
