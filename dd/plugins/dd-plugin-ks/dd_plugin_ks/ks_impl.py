"""
Example external plugin that registers a KS drift detector hookimpl.
This example keeps it toy-level (no scipy dependency).
"""
from __future__ import annotations
import pluggy
from typing import Any, Dict, Optional
from dd.plugins.hookspecs import HookSpecs
from dd.core.io import read_text, write_json

hookimpl = pluggy.HookimplMarker("dd")

class KSDetector:
    name = "ks"

    @staticmethod
    def detect_lines(ref_path: str, cur_path: str) -> Dict[str, Any]:
        # Toy: compare unique line sets overlap ratio as a proxy
        ref = set(read_text(ref_path).splitlines())
        cur = set(read_text(cur_path).splitlines())
        inter = len(ref.intersection(cur))
        union = max(len(ref.union(cur)), 1)
        score = 1.0 - (inter / union)
        return {"score": score, "is_drift": score > 0.3}

@hookimpl
def drift_detect(ref_path: str, cur_path: str, detector: str, cfg: Optional[Dict[str, Any]], output_path: str):
    if detector != "ks":
        return None
    report = KSDetector.detect_lines(ref_path, cur_path)
    report["detector"] = "ks"
    write_json(output_path, report)
    return {"ok": True, "written": output_path, "is_drift": report["is_drift"]}

def register(pm):
    # Option 1: register module (this file) directly
    pm.register(globals(), name="dd_drift_ks")