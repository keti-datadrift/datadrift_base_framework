"""services/experiments.py
High-level experiment utilities around DVC experiments.
- Build experiments dataframe from `dvc exp show --json`
- Apply an experiment and best-effort sync of params.yaml
- Run experiments (immediate, queued, or run-all for queue)
- Push/Pull/Remove experiments helpers
- Fetch Vega-Lite specs from `dvc plots diff --json`
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, List

import pandas as pd
import yaml

from core.constants import DVC_METRIC_DIR, DVC_PARAMS_FILE, PARAM_KEYS
from services.dvc_cli import run_dvc, exp_show, exp_apply, exp_run, plots_diff_json, run_shell


# -------------------------------
# Internal helpers
# -------------------------------

def _extract_values_from_data(data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten DVC exp show 'data' block into param/* and metric/* keys.
    Supports both dvclive-style nested metrics and direct scalar metrics.
    """
    if not isinstance(data_dict, dict):
        return {}

    out: Dict[str, Any] = {}

    # Params
    params = data_dict.get('params', {})
    for _, file_data in params.items():  # e.g. {'params.yaml': {'data': {...}}}
        if isinstance(file_data, dict) and 'data' in file_data:
            for k, v in file_data['data'].items():
                out[f"param/{k}"] = v

    # Metrics (dvclive nested or direct scalars)
    metrics = data_dict.get('metrics', {})
    if DVC_METRIC_DIR in metrics and isinstance(metrics[DVC_METRIC_DIR], dict):
        for k, v in metrics[DVC_METRIC_DIR].items():
            out[f"metric/{k}"] = v
    for k, v in metrics.items():
        if k != DVC_METRIC_DIR and isinstance(v, (int, float, str)):
            out[f"metric/{k}"] = v

    # Timestamps and revision echo if present (defensive)
    if 'timestamp' in data_dict:
        out['Created'] = data_dict['timestamp']
    if 'rev' in data_dict:
        out['SHA'] = data_dict['rev']

    return out


# -------------------------------
# Public API
# -------------------------------

def get_experiments_df(project_root: Path) -> Optional[pd.DataFrame]:
    """Return a normalized DataFrame for experiment overview.
    Columns example: Experiment, Created, metric/*..., param/*..., SHA
    """
    data = exp_show(project_root)
    if not data or not isinstance(data, list):
        return None

    rows: List[Dict[str, Any]] = []
    for item in data:
        vals = _extract_values_from_data(item.get('data', {}))
        rev = item.get('rev')
        name = item.get('name')
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

    # Prefer to show metrics first then params; keep stable order.
    ordered_cols: List[str] = ['Experiment', 'Created']
    ordered_cols += [c for c in df.columns if c.startswith('metric/')]
    ordered_cols += [c for c in df.columns if c.startswith('param/')]
    if 'SHA' in df.columns:
        ordered_cols += ['SHA']
    df = df[[c for c in ordered_cols if c in df.columns]]

    # If YOLO-like mAP exists, sort by it desc
    if 'metric/mAP50' in df.columns:
        df = df.sort_values('metric/mAP50', ascending=False, ignore_index=True)

    return df


def apply_experiment_and_sync_params(exp_rev: str, project_root: Path) -> bool:
    """Apply a DVC experiment and best-effort sync of params.yaml.
    Strategy:
      1) dvc exp apply <rev>
      2) Find that rev in exp_show json and extract its params snapshot
      3) Merge into params.yaml with dotted-key mapping from PARAM_KEYS
    Returns True if apply succeeded (params sync is best-effort and won't fail the call).
    """
    applied = exp_apply(exp_rev, project_root) is not None
    if not applied:
        return False

    data = exp_show(project_root)
    target = None
    for item in (data or []):
        if item.get('rev') == exp_rev:
            target = item
            break
    if not target:
        return True

    # Gather param snapshot (flattened single dict)
    snapshot: Dict[str, Any] = {}
    pdict = target.get('data', {}).get('params', {})
    for _, file_data in pdict.items():
        if isinstance(file_data, dict) and 'data' in file_data:
            snapshot.update(file_data['data'])

    p = Path(project_root) / DVC_PARAMS_FILE
    if not p.exists():
        return True

    try:
        doc = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    except Exception:
        doc = {}

    def set_nested(d: dict, dotted: str, value: Any) -> None:
        cur = d
        parts = dotted.split('.')
        for i, k in enumerate(parts):
            if i == len(parts) - 1:
                cur[k] = value
            else:
                cur = cur.setdefault(k, {})

    # Sync Easy/Advanced shared knobs (if present in snapshot)
    if 'dataset' in snapshot:
        for dotted in PARAM_KEYS.get('dataset_name', []):
            set_nested(doc, dotted, snapshot['dataset'])
    if isinstance(snapshot.get('data'), dict) and 'path' in snapshot['data']:
        for dotted in PARAM_KEYS.get('dataset_path', []):
            set_nested(doc, dotted, snapshot['data']['path'])
    for key, dests in (
        ('epochs', PARAM_KEYS.get('epochs', [])),
        ('imgsz', PARAM_KEYS.get('imgsz', [])),
        ('batch', PARAM_KEYS.get('batch', [])),
    ):
        if key in snapshot:
            for dotted in dests:
                set_nested(doc, dotted, snapshot[key])

    try:
        p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding='utf-8')
    except Exception:
        pass

    return True


def run_experiment(name: str, queue: bool, project_root: Path):
    """Run or queue a DVC experiment."""
    return exp_run(name, queue, project_root)


def run_all_queued(project_root: Path):
    """Run all queued DVC experiments: `dvc exp run --run-all`."""
    return run_dvc(["exp", "run", "--run-all"], project_root)


def remove_experiment(rev_or_name: str, project_root: Path):
    """Remove a DVC experiment by rev or name: `dvc exp remove`."""
    return run_dvc(["exp", "remove", rev_or_name], project_root)


def push_experiments(remote: Optional[str], project_root: Path):
    args = ["exp", "push"] + ([remote] if remote else [])
    return run_dvc(args, project_root)


def pull_experiments(remote: Optional[str], project_root: Path):
    args = ["exp", "pull"] + ([remote] if remote else [])
    return run_dvc(args, project_root)


def list_experiments_raw(project_root: Path):
    """Raw exp show JSON for advanced consumers."""
    return exp_show(project_root)


def get_plots_specs(project_root: Path):
    """Return list of Vega-Lite specs from `dvc plots diff --json`."""
    return plots_diff_json(project_root)
