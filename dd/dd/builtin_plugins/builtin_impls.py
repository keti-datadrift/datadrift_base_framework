"""
First-party minimal implementations to make CLI usable out of the box.
These are intentionally simple no-dependency examples.
"""
from __future__ import annotations
import time
from typing import Any, Dict, Optional
import pluggy
from dd.plugins.hookspecs import HookSpecs
from dd.core.io import read_text, write_text, write_json

hookimpl = pluggy.HookimplMarker("dd")

@hookimpl
def eda_run(input_path: str, modality: str, output_path: str):
    """Toy EDA: count lines/bytes for text-like input."""
    try:
        data = read_text(input_path)
        summary = {
            "modality": modality,
            "lines": len(data.splitlines()),
            "bytes": len(data.encode("utf-8")),
            "preview": data[:100],
            "created_at": time.time(),
        }
        write_json(output_path, summary)
        return {"ok": True, "written": output_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@hookimpl
def transform_apply(input_path: str, transform: str, args: Dict[str, Any], output_path: str):
    """Toy transform: 'upper' or 'lower' for text."""
    try:
        data = read_text(input_path)
        if transform == "text.upper":
            out = data.upper()
        elif transform == "text.lower":
            out = data.lower()
        else:
            out = data  # no-op fallback
        write_text(output_path, out)
        return {"ok": True, "written": output_path, "transform": transform}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@hookimpl
def drift_detect(ref_path: str, cur_path: str, detector: str, cfg: Optional[Dict[str, Any]], output_path: str):
    """Toy drift: compare line counts difference ratio."""
    try:
        ref = read_text(ref_path).splitlines()
        cur = read_text(cur_path).splitlines()
        ref_n, cur_n = len(ref), len(cur)
        diff = abs(ref_n - cur_n)
        ratio = diff / max(ref_n, 1)
        report = {"detector": detector, "ref_lines": ref_n, "cur_lines": cur_n, "diff_ratio": ratio, "is_drift": ratio > 0.1}
        write_json(output_path, report)
        return {"ok": True, "written": output_path, "is_drift": report["is_drift"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@hookimpl
def reconstruct_apply(input_path: str, method: str, args: Dict[str, Any], output_path: str):
    """Toy reconstruction: remove empty lines."""
    try:
        lines = [ln for ln in read_text(input_path).splitlines() if ln.strip()]
        write_text(output_path, "\n".join(lines))
        return {"ok": True, "written": output_path, "method": method}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@hookimpl
def retrain_run(train_path: str, trainer: str, params: Dict[str, Any], model_out: str):
    """Toy training: save a 'model' as a tiny JSON with metadata."""
    try:
        content = read_text(train_path)
        meta = {"trainer": trainer, "params": params, "train_size": len(content), "artifact": model_out}
        write_json(model_out, meta)
        return {"ok": True, "model": model_out}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@hookimpl
def monitor_run(source: str, mode: str, schedule: Optional[str]):
    """Toy monitor: no-op that just acknowledges."""
    return {"ok": True, "mode": mode, "source": source, "scheduled": bool(schedule)}