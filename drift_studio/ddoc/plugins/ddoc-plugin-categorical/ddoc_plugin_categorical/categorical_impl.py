"""Categorical drift detector — jensen_shannon + overlap on dict-of-counts.

The plugin reads a ``distributions.json`` file from each data path
(``data_path_ref/distributions.json`` and
``data_path_cur/distributions.json``) and computes per-attribute
divergence between the two. Output is a standard ddoc drift envelope
with ``modality: "categorical"``.

Distributions JSON shape::

    {
      "color_distribution":      {"red": 10, "blue": 5, "white": 12},
      "type_distribution":       {"sedan": 8, "suv": 7, "truck": 4},
      "hourly_distribution":     {"0": 3, "1": 1, ...}
    }

Each top-level key is one *attribute*. Attribute values are
flat dict-of-counts. ``overall_score`` is the (weighted) mean across
attributes.

The math here matches
``keti_veritas/app/services/dia/comparison.py:jensen_shannon_divergence``
exactly (same base-2 KL average) so any client switching from local
computation to ``ddoc analyze drift --modality=categorical ...`` gets
byte-equivalent scores.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from ddoc.plugins.hookspecs import hookimpl
except ImportError:  # pragma: no cover — installed-but-no-ddoc tests
    def hookimpl(func):  # type: ignore[misc]
        return func


_DISTRIBUTIONS_FILENAME = "distributions.json"
_SUPPORTED_DETECTORS = {"default", "jensen_shannon", "js", "overlap"}


# ── pure functions (no plugin glue) ─────────────────────────────────


def _normalize(dist: Dict[str, float]) -> Dict[str, float]:
    total = sum(dist.values()) or 1.0
    return {k: v / total for k, v in dist.items()}


def jensen_shannon(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Base-2 Jensen-Shannon divergence on count dicts. Symmetric, in [0, 1].

    Mirrors ``keti_veritas.../comparison.py:jensen_shannon_divergence``."""
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    p = _normalize({k: float(a.get(k, 0)) for k in keys})
    q = _normalize({k: float(b.get(k, 0)) for k in keys})
    m = {k: (p[k] + q[k]) / 2.0 for k in keys}

    def _kl(dist: Dict[str, float], ref: Dict[str, float]) -> float:
        s = 0.0
        for k in keys:
            if dist[k] > 0 and ref[k] > 0:
                s += dist[k] * math.log2(dist[k] / ref[k])
        return s

    return (_kl(p, m) + _kl(q, m)) / 2.0


def overlap_distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    """1 - overlap coefficient (0 = identical, 1 = disjoint).

    Returned as a *distance* so higher = more drift, matching
    ``jensen_shannon``'s sign convention."""
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    p = _normalize({k: float(a.get(k, 0)) for k in keys})
    q = _normalize({k: float(b.get(k, 0)) for k in keys})
    overlap = sum(min(p[k], q[k]) for k in keys)
    return 1.0 - overlap


# ── plugin class ────────────────────────────────────────────────────


class CategoricalDriftPlugin:
    """ddoc plugin: ``modality=categorical`` drift detector."""

    def _read_distributions(self, data_path: Optional[str]) -> Optional[Dict[str, Dict[str, float]]]:
        """Load the ``distributions.json`` file under ``data_path``.

        Returns ``None`` if the file is absent (lets other plugins
        try) or malformed (we don't take responsibility for shapes
        we can't make sense of)."""
        if not data_path:
            return None
        path = Path(data_path) / _DISTRIBUTIONS_FILENAME
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        out: Dict[str, Dict[str, float]] = {}
        for attr, dist in data.items():
            if not isinstance(dist, dict):
                continue
            cleaned: Dict[str, float] = {}
            for k, v in dist.items():
                try:
                    cleaned[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue
            if cleaned:
                out[str(attr)] = cleaned
        return out or None

    @hookimpl
    def drift_detect(
        self,
        snapshot_id_ref: str,
        snapshot_id_cur: str,
        data_path_ref: str,
        data_path_cur: str,
        data_hash_ref: str,
        data_hash_cur: str,
        detector: str,
        cfg: Dict[str, Any],
        output_path: str,
    ) -> Optional[Dict[str, Any]]:
        # Inline cfg path (snapshot mode / pre-loaded caches) takes
        # precedence over disk read so callers can short-circuit.
        ref = cfg.get("baseline_categorical") or self._read_distributions(data_path_ref)
        cur = cfg.get("current_categorical") or self._read_distributions(data_path_cur)
        if not ref or not cur:
            # No distributions.json on disk → not our modality. Stay
            # silent so other plugins (timeseries / vision / ...) get
            # a chance.
            return None

        strategy = (detector or "default").lower()
        if strategy not in _SUPPORTED_DETECTORS:
            return {
                "status": "error",
                "error_code": "unsupported_detector",
                "modality": "categorical",
                "message": (
                    f"categorical plugin supports detector ∈ "
                    f"{sorted(_SUPPORTED_DETECTORS)}; got {detector!r}."
                ),
            }
        scorer = (
            overlap_distance if strategy == "overlap"
            else jensen_shannon  # default + js + jensen_shannon all alias to JS
        )

        # Per-attribute scores (intersection of attribute sets).
        attribute_drifts: Dict[str, float] = {}
        for attr in sorted(set(ref) & set(cur)):
            attribute_drifts[attr] = round(scorer(ref[attr], cur[attr]), 4)

        # Optional weights from cfg; default to equal weights.
        weights = cfg.get("attribute_weights") or {}
        if attribute_drifts:
            if isinstance(weights, dict) and weights:
                total_w = sum(weights.get(k, 0.0) for k in attribute_drifts)
                if total_w > 0:
                    overall = sum(
                        attribute_drifts[k] * (weights.get(k, 0.0) / total_w)
                        for k in attribute_drifts
                    )
                else:
                    overall = sum(attribute_drifts.values()) / len(attribute_drifts)
            else:
                overall = sum(attribute_drifts.values()) / len(attribute_drifts)
        else:
            overall = 0.0

        envelope = {
            "status": "success",
            "modality": "categorical",
            "detector": strategy,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "overall_score": round(overall, 4),
            "attribute_drifts": attribute_drifts,
            "ref_attributes": sorted(ref.keys()),
            "cur_attributes": sorted(cur.keys()),
        }

        out = Path(output_path)
        out.mkdir(parents=True, exist_ok=True)
        (out / "metrics.json").write_text(json.dumps(envelope, indent=2),
                                          encoding="utf-8")
        return envelope

    @hookimpl
    def ddoc_supported_detectors(self) -> Dict[str, Any]:
        return {
            "modality": "categorical",
            "default": "jensen_shannon",
            "supported": sorted(_SUPPORTED_DETECTORS),
            "notes": (
                "Operates on dict-of-counts distributions read from "
                "<data_path>/distributions.json (or passed inline via "
                "cfg.baseline_categorical / cfg.current_categorical). "
                "Strategies: jensen_shannon (base-2, symmetric, [0,1]) "
                "or overlap (1 - histogram overlap). Aliases: 'default'/'js' "
                "= jensen_shannon."
            ),
        }

    @hookimpl
    def ddoc_get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "ddoc-plugin-categorical",
            "version": "1.0.0",
            "modality": "categorical",
            "implements": ["drift_detect", "ddoc_supported_detectors"],
            "description": (
                "Categorical-distribution drift via jensen_shannon / "
                "overlap on dict-of-counts. Round 26 (Track A) — closes "
                "the keti vehicle-fingerprint shape gap from Round 25."
            ),
        }
