"""Ingest service — read keti-veritas-style envelope JSON files into ddoc.

This service is the *receiving* side of the keti_veritas → ddoc bridge
defined in `_specs/ddoc_orchestrator_pattern.md` (Phase 5) and
`/Users/jpark/.claude/plans/modular-wandering-tiger.md` (Phase 2).

Source-of-truth shape mirror — frozen dataclass copy of
`keti_veritas/app/services/audit/envelope.py` protocol 1.1. We
*intentionally* do not import keti_veritas as a package; the two
projects ship separately and the schema is the contract.

Layout written to disk (per ingest run, idempotent):

    <workspace>/.ddoc/inbox/<site_id>/
    ├── decisions/
    │   └── decisions_<UTC ts>.csv          # one row per DecisionRecord
    │   └── decisions_<UTC ts>.parquet      # if pyarrow available + parquet flag
    ├── drift_reports/
    │   └── drift_<UTC ts>.json             # one envelope's drift_report payload
    ├── _manifest.jsonl                     # one line per ingest run
    └── .processed/
        └── <original_filename>             # source files that were consumed

Source files are either moved into ``.processed/`` (default) or deleted
when ``mode="delete"``. Re-ingesting a directory is a no-op for files
already in ``.processed/``.
"""

from __future__ import annotations

import csv
import json
import shutil
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from ddoc.core.io import write_json
from ddoc.core.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_PROTOCOLS = frozenset({"1.1"})
DEFAULT_INBOX_REL = ".ddoc/inbox"


# ── Schema mirrors (frozen — keep in sync with keti_veritas envelope) ─


@dataclass(frozen=True)
class IngestEnvelopeSource:
    """Mirror of ``EnvelopeSource`` in keti_veritas/app/services/audit/envelope.py."""

    app_id: str
    app_type: str = "video_forensics"
    instance_id: Optional[str] = None


@dataclass(frozen=True)
class IngestDecisionRecord:
    """Mirror of ``DecisionRecord``. All ``Optional`` fields tolerate None."""

    id: str
    created_at: str
    decision_type: str
    decision: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    threshold_applied: Optional[float] = None
    scores: Optional[dict[str, Any]] = None
    inputs_ref: Optional[dict[str, Any]] = None
    result_summary: Optional[str] = None
    trace: dict[str, Any] = field(default_factory=dict)


# Decision flat-CSV column order. Nested objects are JSON-encoded.
DECISION_CSV_COLUMNS = (
    "id",
    "created_at",
    "decision_type",
    "decision",
    "model_name",
    "model_version",
    "threshold_applied",
    "scores_json",
    "inputs_ref_json",
    "result_summary",
    "trace_json",
    "site_id",
    "ingested_at",
    "source_file",
)


# ── Outcome ────────────────────────────────────────────────────────────


@dataclass
class IngestOutcome:
    """Returned by ``ingest_directory`` so callers (CLI / tests) can report."""

    site_id: str
    inbox_dir: str
    files_seen: int = 0
    files_processed: int = 0
    files_skipped: list[dict[str, Any]] = field(default_factory=list)
    decision_rows: int = 0
    drift_reports: int = 0
    decisions_path: Optional[str] = None
    drift_paths: list[str] = field(default_factory=list)
    manifest_path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Parser ────────────────────────────────────────────────────────────


class EnvelopeError(Exception):
    """Raised when an envelope file fails the protocol 1.1 contract."""


def _parse_envelope(payload: dict[str, Any]) -> tuple[IngestEnvelopeSource, list[IngestDecisionRecord], Optional[dict[str, Any]]]:
    """Validate + lift one envelope JSON dict.

    Returns (source, decision_rows, drift_report). Either the decision
    list or the drift_report (or both) may be empty/None — that's a
    valid envelope shape, just one without that payload kind.
    """
    proto = payload.get("protocol_version")
    if proto not in SUPPORTED_PROTOCOLS:
        raise EnvelopeError(f"unsupported protocol_version: {proto!r}")

    raw_source = payload.get("source") or {}
    if not isinstance(raw_source, dict) or not raw_source.get("app_id"):
        raise EnvelopeError("envelope.source.app_id is required")
    source = IngestEnvelopeSource(
        app_id=str(raw_source["app_id"]),
        app_type=str(raw_source.get("app_type") or "video_forensics"),
        instance_id=raw_source.get("instance_id"),
    )

    kinds = payload.get("payload_kinds") or []
    if not isinstance(kinds, list):
        raise EnvelopeError("envelope.payload_kinds must be a list")

    decisions: list[IngestDecisionRecord] = []
    if "decision_batch" in kinds:
        raw_batch = payload.get("decision_batch") or []
        if not isinstance(raw_batch, list):
            raise EnvelopeError("envelope.decision_batch must be a list")
        for i, row in enumerate(raw_batch):
            if not isinstance(row, dict):
                raise EnvelopeError(f"decision_batch[{i}] is not a dict")
            try:
                decisions.append(IngestDecisionRecord(
                    id=str(row["id"]),
                    created_at=str(row.get("created_at") or ""),
                    decision_type=str(row["decision_type"]),
                    decision=str(row["decision"]),
                    model_name=row.get("model_name"),
                    model_version=row.get("model_version"),
                    threshold_applied=(
                        float(row["threshold_applied"])
                        if row.get("threshold_applied") is not None else None
                    ),
                    scores=row.get("scores"),
                    inputs_ref=row.get("inputs_ref"),
                    result_summary=row.get("result_summary"),
                    trace=row.get("trace") or {},
                ))
            except (KeyError, TypeError, ValueError) as e:
                raise EnvelopeError(
                    f"decision_batch[{i}] malformed: {e}"
                ) from e

    drift_report: Optional[dict[str, Any]] = None
    if "drift_report" in kinds:
        raw = payload.get("drift_report")
        if raw is not None and not isinstance(raw, dict):
            raise EnvelopeError("envelope.drift_report must be an object")
        drift_report = raw

    return source, decisions, drift_report


# ── Writers ────────────────────────────────────────────────────────────


def _write_decisions_csv(
    rows: list[IngestDecisionRecord],
    *,
    out_path: Path,
    site_id: str,
    ingested_at: str,
    source_file: str,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=DECISION_CSV_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "id": r.id,
                "created_at": r.created_at,
                "decision_type": r.decision_type,
                "decision": r.decision,
                "model_name": r.model_name or "",
                "model_version": r.model_version or "",
                "threshold_applied": (
                    "" if r.threshold_applied is None
                    else f"{r.threshold_applied:.6g}"
                ),
                "scores_json": json.dumps(r.scores, ensure_ascii=False) if r.scores else "",
                "inputs_ref_json": json.dumps(r.inputs_ref, ensure_ascii=False) if r.inputs_ref else "",
                "result_summary": r.result_summary or "",
                "trace_json": json.dumps(r.trace, ensure_ascii=False) if r.trace else "",
                "site_id": site_id,
                "ingested_at": ingested_at,
                "source_file": source_file,
            })


def _write_decisions_parquet(
    rows: list[IngestDecisionRecord],
    *,
    out_path: Path,
    site_id: str,
    ingested_at: str,
    source_file: str,
) -> None:
    """Optional parquet writer — only used when ``pyarrow`` is importable.

    Caller is expected to gate on availability; this function will raise
    ``ImportError`` if pyarrow is missing.
    """
    import pyarrow as pa  # type: ignore[import-untyped]
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table({
        "id": [r.id for r in rows],
        "created_at": [r.created_at for r in rows],
        "decision_type": [r.decision_type for r in rows],
        "decision": [r.decision for r in rows],
        "model_name": [r.model_name for r in rows],
        "model_version": [r.model_version for r in rows],
        "threshold_applied": [r.threshold_applied for r in rows],
        "scores_json": [
            json.dumps(r.scores, ensure_ascii=False) if r.scores else None
            for r in rows
        ],
        "inputs_ref_json": [
            json.dumps(r.inputs_ref, ensure_ascii=False) if r.inputs_ref else None
            for r in rows
        ],
        "result_summary": [r.result_summary for r in rows],
        "trace_json": [
            json.dumps(r.trace, ensure_ascii=False) if r.trace else None
            for r in rows
        ],
        "site_id": [site_id] * len(rows),
        "ingested_at": [ingested_at] * len(rows),
        "source_file": [source_file] * len(rows),
    })
    pq.write_table(table, str(out_path))


def _append_manifest(manifest_path: Path, line: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")


# ── Public entry ───────────────────────────────────────────────────────


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _is_envelope_filename(p: Path) -> bool:
    """Heuristic — accept any *.json that's not the manifest itself."""
    return p.is_file() and p.suffix.lower() == ".json" and not p.name.startswith(".")


def ingest_directory(
    *,
    from_dir: Path,
    workspace_root: Path,
    site_id: Optional[str] = None,
    inbox_root: Optional[Path] = None,
    mode: str = "move",
    use_parquet: bool = False,
) -> IngestOutcome:
    """Scan ``from_dir`` for envelope JSON files, ingest each.

    Args:
        from_dir: directory containing envelope JSON files (typically
            keti_veritas's ``DD_EXPORT_DIR``).
        workspace_root: ddoc workspace root. The inbox lives at
            ``<workspace_root>/.ddoc/inbox/<site_id>/`` unless
            ``inbox_root`` overrides.
        site_id: explicit site identifier. If None, falls back to the
            envelope's ``source.app_id``. If multiple envelopes have
            different ``app_id`` values they are all routed to the same
            inbox under the explicit/first-seen id; pass an explicit
            ``site_id`` for stable routing.
        inbox_root: override the default inbox location.
        mode: ``"move"`` (default) places consumed files under
            ``.processed/``; ``"delete"`` removes them.
        use_parquet: write parquet alongside CSV (requires pyarrow).

    Returns:
        ``IngestOutcome`` with counts + paths. Idempotent: files already
        in ``.processed/`` are not re-scanned.
    """
    if mode not in {"move", "delete"}:
        raise ValueError(f"mode must be 'move' or 'delete', got {mode!r}")

    from_dir = Path(from_dir).resolve()
    if not from_dir.is_dir():
        raise FileNotFoundError(f"from_dir does not exist: {from_dir}")
    workspace_root = Path(workspace_root).resolve()

    candidates = sorted(p for p in from_dir.iterdir() if _is_envelope_filename(p))
    files_seen = len(candidates)

    if not candidates:
        # Empty pass is still valid — return outcome with site fallback.
        site = site_id or "default"
        inbox_dir = (inbox_root or (workspace_root / DEFAULT_INBOX_REL)) / site
        return IngestOutcome(site_id=site, inbox_dir=str(inbox_dir),
                             files_seen=0, files_processed=0)

    # First pass — read first valid envelope to resolve site_id when caller didn't pass one.
    resolved_site = site_id
    parsed: list[tuple[Path, IngestEnvelopeSource, list[IngestDecisionRecord], Optional[dict[str, Any]]]] = []
    skipped: list[dict[str, Any]] = []
    for p in candidates:
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            src, decisions, drift = _parse_envelope(payload)
        except (json.JSONDecodeError, EnvelopeError) as e:
            skipped.append({"file": p.name, "reason": str(e)})
            continue
        if resolved_site is None:
            resolved_site = src.app_id
        parsed.append((p, src, decisions, drift))

    if not parsed:
        return IngestOutcome(
            site_id=resolved_site or "default",
            inbox_dir=str((inbox_root or (workspace_root / DEFAULT_INBOX_REL))
                          / (resolved_site or "default")),
            files_seen=files_seen, files_processed=0, files_skipped=skipped,
        )

    site = resolved_site or "default"
    inbox_dir = (inbox_root or (workspace_root / DEFAULT_INBOX_REL)) / site
    decisions_dir = inbox_dir / "decisions"
    drift_dir = inbox_dir / "drift_reports"
    processed_dir = inbox_dir / ".processed"
    manifest_path = inbox_dir / "_manifest.jsonl"

    # Aggregate all decisions across this run into one CSV file (idempotency:
    # filename keyed on UTC timestamp, source-file column tracks origin).
    all_decisions: list[IngestDecisionRecord] = []
    drift_paths: list[str] = []
    drift_count = 0
    files_processed = 0

    ingested_at = datetime.now(timezone.utc).isoformat()
    ts = _utc_ts()
    decisions_csv = decisions_dir / f"decisions_{ts}.csv"
    decisions_parquet = decisions_dir / f"decisions_{ts}.parquet"

    # Use one CSV writer shared across all envelopes in this pass — keep
    # source_file column populated per-row for provenance.
    decisions_dir.mkdir(parents=True, exist_ok=True)
    csv_handle = decisions_csv.open("w", encoding="utf-8", newline="")
    writer = csv.DictWriter(csv_handle, fieldnames=DECISION_CSV_COLUMNS)
    writer.writeheader()

    try:
        for src_path, src, decisions, drift in parsed:
            for r in decisions:
                writer.writerow({
                    "id": r.id,
                    "created_at": r.created_at,
                    "decision_type": r.decision_type,
                    "decision": r.decision,
                    "model_name": r.model_name or "",
                    "model_version": r.model_version or "",
                    "threshold_applied": (
                        "" if r.threshold_applied is None
                        else f"{r.threshold_applied:.6g}"
                    ),
                    "scores_json": json.dumps(r.scores, ensure_ascii=False) if r.scores else "",
                    "inputs_ref_json": json.dumps(r.inputs_ref, ensure_ascii=False) if r.inputs_ref else "",
                    "result_summary": r.result_summary or "",
                    "trace_json": json.dumps(r.trace, ensure_ascii=False) if r.trace else "",
                    "site_id": site,
                    "ingested_at": ingested_at,
                    "source_file": src_path.name,
                })
                all_decisions.append(r)

            if drift is not None:
                drift_dir.mkdir(parents=True, exist_ok=True)
                drift_out = drift_dir / f"drift_{ts}_{src_path.stem}.json"
                write_json(str(drift_out), {
                    "site_id": site,
                    "source_file": src_path.name,
                    "ingested_at": ingested_at,
                    "report": drift,
                })
                drift_paths.append(str(drift_out))
                drift_count += 1

            # Mark consumed
            if mode == "move":
                processed_dir.mkdir(parents=True, exist_ok=True)
                target = processed_dir / src_path.name
                # Idempotency: if same name already exists in processed, append a counter.
                if target.exists():
                    target = processed_dir / f"{src_path.stem}.{uuid.uuid4().hex[:8]}{src_path.suffix}"
                shutil.move(str(src_path), str(target))
            else:  # delete
                src_path.unlink(missing_ok=True)

            files_processed += 1
    finally:
        csv_handle.close()

    # If no decision rows landed in this pass, drop the empty CSV.
    if not all_decisions:
        try:
            decisions_csv.unlink()
        except FileNotFoundError:
            pass
        decisions_csv_path: Optional[str] = None
    else:
        decisions_csv_path = str(decisions_csv)

    # Optional parquet output
    if use_parquet and all_decisions:
        try:
            _write_decisions_parquet(
                all_decisions, out_path=decisions_parquet,
                site_id=site, ingested_at=ingested_at,
                source_file="<aggregated>",
            )
        except ImportError:
            logger.warning(
                "[ingest] use_parquet=True but pyarrow unavailable — skipping parquet"
            )

    # Manifest line
    manifest_line = {
        "ingested_at": ingested_at,
        "site_id": site,
        "files_seen": files_seen,
        "files_processed": files_processed,
        "files_skipped": len(skipped),
        "decision_rows": len(all_decisions),
        "drift_reports": drift_count,
        "decisions_csv": decisions_csv_path,
        "drift_paths": drift_paths,
    }
    _append_manifest(manifest_path, manifest_line)

    return IngestOutcome(
        site_id=site,
        inbox_dir=str(inbox_dir),
        files_seen=files_seen,
        files_processed=files_processed,
        files_skipped=skipped,
        decision_rows=len(all_decisions),
        drift_reports=drift_count,
        decisions_path=decisions_csv_path,
        drift_paths=drift_paths,
        manifest_path=str(manifest_path),
    )
