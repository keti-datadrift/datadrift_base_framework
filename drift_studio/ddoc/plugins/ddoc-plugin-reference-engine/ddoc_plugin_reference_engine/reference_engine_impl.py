"""ddoc plugin: reference-selection-function ladder (drift_tool_analysis.md 3부). Round 34.

Adapted to this repo's current conventions (confirmed via direct source
inspection, not assumption):

1. Detector dispatch is now broadcast + self-filter: every installed
   plugin's `drift_detect` is called, and each returns `None` if `detector`
   doesn't match its own prefix (see ddoc-plugin-keti-temporal for the
   pattern this follows). This plugin engages only on `detector ==
   "reference_engine"` -- it deliberately does NOT claim "default" for the
   `timeseries` modality, since ddoc-plugin-timeseries already owns that
   slot; this stays a separate, explicitly-requested detector, matching how
   ddoc-plugin-keti-temporal/ddoc-plugin-evidently avoid hijacking defaults.
2. `ddoc_supported_detectors` is implemented (Round-13/Gap-5 convention) so
   `ddoc analyze drift --detector reference_engine` fails fast with a clear
   message if this plugin isn't installed, instead of a silent no-op.
3. `eda_run` no longer needs the legacy-cache read-merge-write workaround
   from the prior (stale) version of this repo -- `cache_service.
   find_attribute_caches()` now resolves any `attributes_*` namespaced
   cache on its own (core/cache_service.py), so writing to the namespaced
   `attributes_reference_engine` key alone is sufficient.
4. The modality-merge collision bug is UNCHANGED upstream
   (`_merge_plugin_results` in cli/commands/analyze/drift.py still does
   `merged["modalities"][modality] = result`, last-write-wins on collision)
   -- this plugin still uses the distinct `"timeseries_reference"` modality
   (not `"timeseries"`) to coexist with ddoc-plugin-timeseries.
5. Envelope shape follows the de facto convention other plugins use
   (`status/backend/detector/method/overall_score/attribute_drifts/...`),
   confirmed via ddoc-plugin-keti-temporal's plugin.py -- there is no
   enforced Pydantic schema (server/schemas.py explicitly avoids
   double-validating), but conforming to this shape keeps `report.render`/
   `--fusion` compatible.

drift_detect reconciles ddoc's snapshot-diff model (compare two point-in-time
datasets) with the ladder's time-series model (one continuously-growing
series, evaluated against history computed from itself): data_path_cur is
treated as the full series including the newest data; the evaluation window
is "dates present in cur but not in ref" (new since the baseline snapshot),
falling back to the last 30 days if ref can't be read. History for the ladder
(YoY lookback, STL fit) is drawn from data_path_cur strictly before the
window start -- see reference_functions.py's `history_end` parameter.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

try:
    from ddoc.plugins.hookspecs import hookimpl
except ImportError:
    def hookimpl(func):
        return func

from .dataset_discovery import discover_timeseries_datasets, load_dataset_frame, extract_column_series
from .event_store import get_event_store
from .reference_functions import (
    level0_fixed_baseline, level1_yoy_dual_basis, level2_regime_redefinition,
    level3_decomposition, level4_intervention_adjusted,
)

MODALITY = "timeseries_reference"
DETECTOR = "reference_engine"
FALLBACK_WINDOW_DAYS = 30


def _summarize_column(series: pd.DataFrame) -> Dict[str, Any]:
    return {
        "count": int(len(series)),
        "mean": float(series["value"].mean()),
        "std": float(series["value"].std()) if len(series) > 1 else 0.0,
        "min": float(series["value"].min()),
        "max": float(series["value"].max()),
        "date_start": str(series["date"].min().date()),
        "date_end": str(series["date"].max().date()),
    }


def _numeric_columns(config: Dict[str, Any]):
    return config.get("numeric_columns", [])


def _sanitize_records(df: pd.DataFrame) -> list:
    """DataFrame -> list[dict] with NaN replaced by None. Bare NaN survives
    json.dumps(default=str) as an invalid (non-RFC8259) literal `NaN` token
    -- pandas leaves it in float columns like `effective_date` for rows that
    came from the intervention log (which has no such column). Found via
    the path-mode CLI smoke test, not by inspection -- an agent consuming
    this JSON with a strict parser would fail on it."""
    if df.empty:
        return []
    return [
        {k: (None if isinstance(v, float) and v != v else v) for k, v in record.items()}
        for record in df.to_dict(orient="records")
    ]


def _err(detector: str, message: str) -> Dict[str, Any]:
    return {
        "status": "error", "backend": "reference-engine", "detector": detector,
        "message": message, "overall_score": None, "attribute_drifts": None,
    }


class ReferenceEnginePlugin:
    """레퍼런스 선택 함수 성숙도 사다리(레벨0~4) + 이벤트 온톨로지 ddoc 플러그인."""

    @hookimpl
    def ddoc_get_metadata(self):
        return {
            "name": "ddoc-plugin-reference-engine",
            "description": "레퍼런스 선택 함수 성숙도 사다리(레벨0~4, alert/quiet/deferred) + 이벤트 온톨로지",
            "hooks_implemented": ["eda_run", "drift_detect", "ddoc_supported_detectors"],
            "modality": MODALITY,
        }

    @hookimpl
    def ddoc_supported_detectors(self) -> Optional[Dict[str, Any]]:
        return {
            "modality": MODALITY,
            "default": DETECTOR,
            "supported": [DETECTOR],
            "notes": (
                "레벨0(고정기준선)/레벨1(전년동일병기)/레벨2(레짐재정의)/"
                "레벨3(STL계절분해)/레벨4(개입보정) 사다리를 한 번에 계산해 "
                "alert/quiet/deferred 3상태로 반환. 단일 스코어가 아니라 "
                "results[col].levels 아래 5개 레벨을 전부 담아 돌려줌."
            ),
        }

    @hookimpl
    def eda_run(self, snapshot_id, data_path, data_hash, output_path, invalidate_cache=False):
        from ddoc.core.cache_service import get_cache_service

        cache_service = get_cache_service()
        input_path = Path(data_path)
        out_path = Path(output_path)
        out_path.mkdir(parents=True, exist_ok=True)

        datasets = discover_timeseries_datasets(input_path)
        if not datasets:
            return None

        summaries: Dict[str, Any] = {}
        for dataset_path, config in datasets:
            try:
                df = load_dataset_frame(dataset_path, config)
            except Exception as e:
                print(f"reference-engine: skipping {dataset_path.name} ({e})")
                continue
            timestamp_col = config["timestamp_column"]
            for col in _numeric_columns(config):
                if col not in df.columns:
                    continue
                col_key = f"{dataset_path.name}/{col}"
                try:
                    series = extract_column_series(df, timestamp_col, col)
                    summaries[col_key] = _summarize_column(series)
                except Exception as e:
                    print(f"reference-engine: skipping column {col_key} ({e})")

        if not summaries:
            return None

        # Path mode passes an empty data_hash (no snapshot context) --
        # caching is the orchestrator's job then, same convention as
        # ddoc-plugin-timeseries's Round-6 fix.
        if data_hash:
            cache_service.save_analysis_cache(
                snapshot_id=snapshot_id, data_hash=data_hash,
                cache_type="attributes_reference_engine", data=summaries,
            )

        metrics = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "snapshot_id": snapshot_id, "data_hash": data_hash,
            "modality": MODALITY, "series_analyzed": len(summaries),
        }
        (out_path / "metrics.json").write_text(json.dumps(metrics, indent=2))

        return {
            "status": "success", "modality": MODALITY,
            "series_analyzed": len(summaries), "summary": metrics,
        }

    @hookimpl
    def drift_detect(
        self, snapshot_id_ref: str, snapshot_id_cur: str,
        data_path_ref: str, data_path_cur: str,
        data_hash_ref: str, data_hash_cur: str,
        detector: str, cfg: Dict[str, Any], output_path: str,
    ) -> Optional[Dict[str, Any]]:
        strategy = (detector or "").lower()
        if strategy != DETECTOR:
            return None  # explicit opt-in only, matching keti-temporal/evidently's convention
            # (not "default" -- ddoc-plugin-timeseries already owns that slot for this modality)

        out_path = Path(output_path)
        out_path.mkdir(parents=True, exist_ok=True)

        cur_datasets = discover_timeseries_datasets(Path(data_path_cur))
        if not cur_datasets:
            return None
        ref_datasets = {p.name: (p, c) for p, c in discover_timeseries_datasets(Path(data_path_ref or ""))}

        event_store = get_event_store()
        intervention_log = event_store.load_intervention_log(confirmed_only=True)
        regime_log = event_store.load_regime_log(confirmed_only=True)

        results: Dict[str, Any] = {}
        new_candidates = []

        for dataset_path, config in cur_datasets:
            timestamp_col = config["timestamp_column"]
            try:
                cur_df = load_dataset_frame(dataset_path, config)
            except Exception as e:
                print(f"reference-engine: skipping {dataset_path.name} ({e})")
                continue

            ref_entry = ref_datasets.get(dataset_path.name)

            for col in _numeric_columns(config):
                if col not in cur_df.columns:
                    continue
                col_key = f"{dataset_path.name}/{col}"
                try:
                    cur_series = extract_column_series(cur_df, timestamp_col, col)
                    if cur_series.empty:
                        continue

                    window_start, window_end = self._evaluation_window(cur_series, ref_entry, col)

                    levels = [
                        level0_fixed_baseline(cur_series, window_start, window_end),
                        level1_yoy_dual_basis(cur_series, window_start, window_end),
                        level2_regime_redefinition(cur_series, window_start, window_end, regime_log, col_key),
                        level3_decomposition(cur_series, window_start, window_end, history_end=window_start),
                        level4_intervention_adjusted(cur_series, window_start, window_end, intervention_log, col_key, history_end=window_start),
                    ]
                    results[col_key] = {
                        "evaluation_window": {"start": str(window_start.date()), "end": str(window_end.date())},
                        "levels": {r.level: r.to_dict() for r in levels},
                    }

                    new_candidates += event_store.detect_candidate_events(cur_series, col_key)
                except Exception as e:
                    print(f"reference-engine: skipping {col_key} ({e})")

        if not results:
            return None

        # attribute_drifts / overall_score: de facto envelope fields other
        # plugins populate (see keti-temporal). We derive a coarse
        # 0/0.5/1 proxy per column from the L3 status so --fusion has
        # something numeric to combine, while the real payload (per-level
        # alert/quiet/deferred + reasons) lives in `results`.
        _status_score = {"quiet": 0.0, "deferred": 0.5, "alert": 1.0}
        attribute_drifts = {
            col: _status_score[body["levels"]["L3_계절분해"]["status"]]
            for col, body in results.items()
        }
        overall_score = round(sum(attribute_drifts.values()) / len(attribute_drifts), 4)

        pending = event_store.list_candidate_events()
        output = {
            "status": "success",
            "backend": "reference-engine",
            "detector": DETECTOR,
            "method": "level0-4_ladder",
            "modality": MODALITY,
            "overall_score": overall_score,
            "attribute_drifts": attribute_drifts,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "results": results,
            "new_candidate_events": new_candidates,
            "pending_candidate_events": _sanitize_records(pending),
        }
        (out_path / "metrics.json").write_text(json.dumps(output, indent=2, default=str))
        return output

    @staticmethod
    def _evaluation_window(cur_series: pd.DataFrame, ref_entry, col: str):
        """'ref에는 없고 cur에는 있는' 날짜 구간 = 평가 대상. ref를 못 읽으면
        최근 FALLBACK_WINDOW_DAYS일로 대체한다."""
        cur_max = cur_series["date"].max()
        if ref_entry is not None:
            ref_path, ref_config = ref_entry
            try:
                ref_df = load_dataset_frame(ref_path, ref_config)
                if col in ref_df.columns:
                    ref_series = extract_column_series(ref_df, ref_config["timestamp_column"], col)
                    if not ref_series.empty:
                        ref_max = ref_series["date"].max()
                        if ref_max < cur_max:
                            return ref_max + pd.Timedelta(days=1), cur_max
            except Exception:
                pass
        return cur_max - pd.Timedelta(days=FALLBACK_WINDOW_DAYS - 1), cur_max
