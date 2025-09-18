"""
Ultra-minimal linear pipeline for MVP (no DAG yet).
Each step is a CLI-equivalent operation resolved by plugins.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from dd.core.plugins import get_plugin_manager
from dd.core.logging import get_logger

log = get_logger(__name__)

class PipelineRunner:
    def __init__(self) -> None:
        self.pm = get_plugin_manager().pm

    def run(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for idx, step in enumerate(steps, start=1):
            typ = step.get("type")
            log.info("Running step %d: %s", idx, typ)
            if typ == "eda":
                res = self.pm.hook.eda_run(
                    input_path=step["input"],
                    modality=step.get("modality", "table"),
                    output_path=step.get("out", "report.json"),
                )
            elif typ == "transform":
                res = self.pm.hook.transform_apply(
                    input_path=step["input"],
                    transform=step["transform"],
                    args=step.get("args", {}),
                    output_path=step.get("out", "out"),
                )
            elif typ == "drift":
                res = self.pm.hook.drift_detect(
                    ref_path=step["ref"],
                    cur_path=step["cur"],
                    detector=step.get("detector", "ks"),
                    cfg=step.get("cfg"),
                    output_path=step.get("out", "drift.json"),
                )
            elif typ == "reconstruct":
                res = self.pm.hook.reconstruct_apply(
                    input_path=step["input"],
                    method=step["method"],
                    args=step.get("args", {}),
                    output_path=step.get("out", "recon_out"),
                )
            elif typ == "retrain":
                res = self.pm.hook.retrain_run(
                    train_path=step["train"],
                    trainer=step.get("trainer", "sklearn"),
                    params=step.get("params", {}),
                    model_out=step.get("model_out", "model.bin"),
                )
            elif typ == "monitor":
                res = self.pm.hook.monitor_run(
                    source=step["source"],
                    mode=step.get("mode", "offline"),
                    schedule=step.get("schedule"),
                )
            else:
                raise ValueError(f"Unknown step type: {typ}")

            # hook calls return a list (one per plugin); collect light results
            results.append({"type": typ, "result": _first_non_none(res)})
        return results

def _first_non_none(seq):
    for x in seq:
        if x is not None:
            return x
    return None