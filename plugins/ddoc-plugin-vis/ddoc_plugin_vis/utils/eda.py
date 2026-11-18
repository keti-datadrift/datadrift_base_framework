from pathlib import Path
from typing import Dict
from services.dataset_manager import scan_stats


def summarize_dataset(ds_dir: Path) -> Dict[str, float]:
    return scan_stats(ds_dir)


def diff_stats(left: Dict[str, float], right: Dict[str, float]) -> Dict[str, float]:
    keys = set(left) | set(right)
    return {k: float(right.get(k, 0.0) - left.get(k, 0.0)) for k in keys}