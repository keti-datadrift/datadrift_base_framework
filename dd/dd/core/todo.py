# dd/core/contracts.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class DriftReport(Dict[str, Any]):
    """Typed dict for drift results."""

class DriftDetector(ABC):
    """Drift detector contract."""
    name: str = "base"

    @abstractmethod
    def fit(self, ref_dataset) -> None:
        """Fit on reference dataset (baseline)."""

    @abstractmethod
    def detect(self, cur_dataset) -> DriftReport:
        """Return drift metrics and flags."""