"""
Builtin implementations with optional hookspec version range and priorities.
"""
import time
import pluggy
from typing import Any, Dict, Optional
from ddoc.core.io import read_text, write_text, write_json

hookimpl = pluggy.HookimplMarker("ddoc")

# Builtin declares compatibility window (optional)
DDOC_HOOKSPEC_MIN = "1.0.0"
DDOC_HOOKSPEC_MAX = "1.999.999"

# Removed: eda_run and drift_detect builtin implementations
# These were text file fallback handlers that caused confusion with multi-modal plugins.
# Text analysis is now handled by dedicated plugins (ddoc-plugin-text).

@hookimpl  # default priority
def transform_apply(input_path: str, transform: str, args: Dict[str, Any], output_path: str):
    try:
        data = read_text(input_path)
        if transform == "text.upper":
            out = data.upper()
        elif transform == "text.lower":
            out = data.lower()
        else:
            out = data
        write_text(output_path, out)
        return {"ok": True, "written": output_path, "transform": transform}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# Removed: drift_detect builtin implementation (see comment above)

@hookimpl
def reconstruct_apply(input_path: str, method: str, args: Dict[str, Any], output_path: str):
    try:
        lines = [ln for ln in read_text(input_path).splitlines() if ln.strip()]
        write_text(output_path, "\n".join(lines))
        return {"ok": True, "written": output_path, "method": method}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@hookimpl
def retrain_run(train_path: str, trainer: str, params: Dict[str, Any], model_out: str):
    try:
        content = read_text(train_path)
        meta = {"trainer": trainer, "params": params, "train_size": len(content), "artifact": model_out}
        write_json(model_out, meta)
        return {"ok": True, "model": model_out}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@hookimpl
def monitor_run(source: str, mode: str, schedule: Optional[str]):
    return {"ok": True, "mode": mode, "source": source, "scheduled": bool(schedule)}