"""ddoc.yaml scanning convention, reused from ddoc-plugin-timeseries
(timeseries_impl.py's `_load_ddoc_yaml`/`_compute_attributes_from_path`) --
confirmed unchanged in this repo version. This is the only part of that
plugin's scaffolding worth reusing; its statistical logic is replaced
entirely (see reference_functions.py's module docstring). Round 34.
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd
import yaml


def load_ddoc_yaml(dataset_path: Path) -> Dict[str, Any]:
    yaml_path = dataset_path / "ddoc.yaml"
    if not yaml_path.exists():
        raise ValueError(f"ddoc.yaml not found in {dataset_path}")
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)
    if config.get("modality") != "timeseries":
        raise ValueError(f"Dataset {dataset_path} is not configured as timeseries modality")
    if "csv_file" not in config:
        raise ValueError("ddoc.yaml must specify 'csv_file'")
    if "timestamp_column" not in config:
        raise ValueError("ddoc.yaml must specify 'timestamp_column'")
    return config


def discover_timeseries_datasets(input_path: Path) -> List[Tuple[Path, Dict[str, Any]]]:
    """Scan input_path's subdirectories for ddoc.yaml files with modality: timeseries."""
    datasets = []
    if not input_path.exists():
        return datasets
    for item in sorted(input_path.iterdir()):
        if item.is_dir():
            try:
                config = load_ddoc_yaml(item)
                datasets.append((item, config))
            except Exception:
                continue
    return datasets


def load_dataset_frame(dataset_path: Path, config: Dict[str, Any]) -> pd.DataFrame:
    """Load a dataset's raw CSV with its timestamp column parsed and sorted."""
    csv_file = dataset_path / config["csv_file"]
    df = pd.read_csv(csv_file)
    timestamp_col = config["timestamp_column"]
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    return df.sort_values(timestamp_col).reset_index(drop=True)


def extract_column_series(df: pd.DataFrame, timestamp_col: str, value_col: str) -> pd.DataFrame:
    """Reshape one numeric column into the (date, value) long format
    reference_functions.py's ladder expects."""
    out = df[[timestamp_col, value_col]].rename(columns={timestamp_col: "date", value_col: "value"})
    return out.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)
