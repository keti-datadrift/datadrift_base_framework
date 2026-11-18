"""Effect-size statistics reused from the backend's image-drift path.

Copied (not imported) from drift_studio/backend/app/services/drift_service.py
because the backend has no pyproject.toml (not pip-installable) and no
existing ddoc plugin imports another plugin's package -- copying with
provenance comments is the established convention here, not a shortcut.

Source: drift_studio/backend/app/services/drift_service.py
  - calculate_kl_divergence: ~lines 560-583
  - calculate_psi:           ~lines 627-643
"""
import numpy as np


def calculate_kl_divergence(p, q, bins: int = 20) -> float:
    """KL divergence between two 1-D samples via shared-range histograms."""
    try:
        min_val = min(min(p), min(q))
        max_val = max(max(p), max(q))

        p_hist, edges = np.histogram(p, bins=bins, range=(min_val, max_val), density=True)
        q_hist, _ = np.histogram(q, bins=edges, density=True)

        p_hist = p_hist + 1e-10
        q_hist = q_hist + 1e-10
        p_hist = p_hist / p_hist.sum()
        q_hist = q_hist / q_hist.sum()

        kl = float(np.sum(p_hist * np.log(p_hist / q_hist)))
        return round(abs(kl), 4)
    except Exception:
        return 0.0


def calculate_psi(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index between a baseline and current 1-D sample."""
    try:
        min_val = min(baseline.min(), current.min())
        max_val = max(baseline.max(), current.max())
        edges = np.linspace(min_val, max_val, bins + 1)

        baseline_hist, _ = np.histogram(baseline, bins=edges)
        current_hist, _ = np.histogram(current, bins=edges)

        baseline_prop = (baseline_hist + 1) / (baseline_hist.sum() + bins)
        current_prop = (current_hist + 1) / (current_hist.sum() + bins)

        psi = np.sum((current_prop - baseline_prop) * np.log(current_prop / baseline_prop))
        return round(float(abs(psi)), 4)
    except Exception:
        return 0.0
