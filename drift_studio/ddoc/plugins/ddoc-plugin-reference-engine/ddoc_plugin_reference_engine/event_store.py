"""Event ontology (intervention_log + regime_log) as this plugin's own persistent
store -- context_workplace/drift_tool_analysis.md 10부/12부. Round 34.

No hookspec models a stateful event registry today (all 12 original hooks
plus the 4 new Round-11/13 hooks are stateless), and no existing plugin
imports another plugin's package -- extending core hookspecs.py for a shared
event_register/event_list hook is a considered v2 follow-up, not this slice.
Storage mirrors the existing `.ddoc/cache/` convention (flat files under a
`.ddoc/` subdirectory of the project root).

Two event types, matching drift_tool_analysis.md's level2/level4 distinction:
- intervention: temporary, reverting (e.g. a marketing campaign) -- level4
- regime: permanent, non-reverting (e.g. a platform migration) -- level2

Auto-detected anomalies are written as *candidates* (confirmed=False) --
drift_tool_analysis.md 10.4's "agent proposes, human approves" pattern. Only
confirmed events are used by level2_regime_redefinition/level4_intervention_adjusted
by default.
"""
from pathlib import Path
from typing import Optional
import uuid
import numpy as np
import pandas as pd
import yaml

INTERVENTION_COLUMNS = ["event_id", "event_type", "series", "start", "end", "description", "confirmed", "proposed_by"]
REGIME_COLUMNS = ["event_id", "series", "effective_date", "description", "confirmed", "proposed_by"]


class EventStore:
    """Flat-YAML event store under `<project_root>/.ddoc/events/`."""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.events_dir = self.project_root / ".ddoc" / "events"
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self._intervention_file = self.events_dir / "intervention_log.yaml"
        self._regime_file = self.events_dir / "regime_log.yaml"

    # -- low-level read/write -------------------------------------------------

    def _load_raw(self, path: Path) -> list:
        if not path.exists():
            return []
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return data or []

    def _save_raw(self, path: Path, rows: list):
        with open(path, "w") as f:
            yaml.safe_dump(rows, f, allow_unicode=True, sort_keys=False)

    # -- intervention log (level4: temporary, reverting) -----------------------

    def register_intervention(self, series: str, start: str, end: str, description: str,
                               event_type: str = "manual", confirmed: bool = True,
                               proposed_by: str = "human") -> str:
        event_id = f"iv_{uuid.uuid4().hex[:10]}"
        rows = self._load_raw(self._intervention_file)
        rows.append({
            "event_id": event_id, "event_type": event_type, "series": series,
            "start": str(start), "end": str(end), "description": description,
            "confirmed": confirmed, "proposed_by": proposed_by,
        })
        self._save_raw(self._intervention_file, rows)
        return event_id

    def load_intervention_log(self, confirmed_only: bool = True) -> pd.DataFrame:
        rows = self._load_raw(self._intervention_file)
        df = pd.DataFrame(rows, columns=INTERVENTION_COLUMNS)
        if confirmed_only and not df.empty:
            df = df[df["confirmed"] == True]  # noqa: E712
        return df

    # -- regime log (level2: permanent, non-reverting) --------------------------

    def register_regime(self, series: str, effective_date: str, description: str,
                         confirmed: bool = True, proposed_by: str = "human") -> str:
        event_id = f"rg_{uuid.uuid4().hex[:10]}"
        rows = self._load_raw(self._regime_file)
        rows.append({
            "event_id": event_id, "series": series, "effective_date": str(effective_date),
            "description": description, "confirmed": confirmed, "proposed_by": proposed_by,
        })
        self._save_raw(self._regime_file, rows)
        return event_id

    def load_regime_log(self, confirmed_only: bool = True) -> pd.DataFrame:
        rows = self._load_raw(self._regime_file)
        df = pd.DataFrame(rows, columns=REGIME_COLUMNS)
        if confirmed_only and not df.empty:
            df = df[df["confirmed"] == True]  # noqa: E712
        return df

    # -- candidate review queue -------------------------------------------------

    def list_candidate_events(self) -> pd.DataFrame:
        """Unconfirmed rows from both logs, tagged by which log they came from."""
        iv = self.load_intervention_log(confirmed_only=False)
        rg = self.load_regime_log(confirmed_only=False)
        iv = iv[iv["confirmed"] == False].assign(log="intervention") if not iv.empty else iv  # noqa: E712
        rg = rg[rg["confirmed"] == False].assign(log="regime") if not rg.empty else rg  # noqa: E712
        return pd.concat([iv, rg], ignore_index=True, sort=False)

    def confirm_event(self, event_id: str) -> bool:
        """Approve a candidate event so level2/level4 will start using it."""
        for path, columns in [(self._intervention_file, INTERVENTION_COLUMNS), (self._regime_file, REGIME_COLUMNS)]:
            rows = self._load_raw(path)
            changed = False
            for row in rows:
                if row.get("event_id") == event_id:
                    row["confirmed"] = True
                    changed = True
            if changed:
                self._save_raw(path, rows)
                return True
        return False

    # -- auto-detection: propose candidate intervention events -------------------

    def detect_candidate_events(self, series_df: pd.DataFrame, series_name: str,
                                 z_threshold: float = 5.0, window: int = 30) -> list:
        """10.4: flag individual days whose deviation from a trailing rolling
        window is extreme (stricter than the ladder's own 3.0 threshold, to
        keep auto-proposals high-precision) and write them as unconfirmed
        intervention candidates for human/agent review. Returns the list of
        newly proposed event_ids (empty if nothing crossed the threshold)."""
        s = series_df.sort_values("date").reset_index(drop=True)
        rolling_mean = s["value"].rolling(window, min_periods=max(window // 2, 5)).mean().shift(1)
        rolling_sd = s["value"].rolling(window, min_periods=max(window // 2, 5)).std().shift(1)
        z = (s["value"] - rolling_mean) / rolling_sd.replace(0, np.nan)

        existing = self.load_intervention_log(confirmed_only=False)
        already_flagged = set(existing["start"]) if not existing.empty else set()

        proposed = []
        for i in np.where(np.abs(z.values) > z_threshold)[0]:
            date_str = str(s.loc[i, "date"].date())
            if date_str in already_flagged:
                continue
            event_id = self.register_intervention(
                series=series_name, start=date_str, end=date_str,
                description=f"자동탐지: {date_str} 값이 직전 {window}일 대비 z={z.iloc[i]:+.1f}",
                event_type="auto_detected_outlier", confirmed=False, proposed_by="auto_detection",
            )
            proposed.append(event_id)
        return proposed


def get_event_store(project_root: Optional[str] = None) -> EventStore:
    return EventStore(project_root)
