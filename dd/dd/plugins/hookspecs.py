"""
Hook specifications for dd plugin system.

Each hook returns a dictionary-like result where applicable.
Only minimal, stable contracts for MVP are defined here.
"""
import pluggy
from typing import Any, Dict, Optional

hookspec = pluggy.HookspecMarker("dd")

class HookSpecs:
    @hookspec
    def eda_run(self, input_path: str, modality: str, output_path: str) -> Optional[Dict[str, Any]]:
        """Run EDA and write a report to output_path. Return a brief summary."""

    @hookspec
    def transform_apply(self, input_path: str, transform: str, args: Dict[str, Any], output_path: str) -> Optional[Dict[str, Any]]:
        """Apply a named transform and write result to output_path."""

    @hookspec
    def drift_detect(self, ref_path: str, cur_path: str, detector: str, cfg: Optional[Dict[str, Any]], output_path: str) -> Optional[Dict[str, Any]]:
        """Detect drift between ref and cur datasets, write report, return brief metrics."""

    @hookspec
    def reconstruct_apply(self, input_path: str, method: str, args: Dict[str, Any], output_path: str) -> Optional[Dict[str, Any]]:
        """Reconstruct/Impute/Resample data and write result."""

    @hookspec
    def retrain_run(self, train_path: str, trainer: str, params: Dict[str, Any], model_out: str) -> Optional[Dict[str, Any]]:
        """Retrain model and write model artifact."""

    @hookspec
    def monitor_run(self, source: str, mode: str, schedule: Optional[str]) -> Optional[Dict[str, Any]]:
        """Run monitors once or in a scheduled fashion (no scheduler built-in in MVP)."""