"""Tests for the ``ddoc ingest`` command + ingest_service."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ddoc.core.ingest_service import (
    EnvelopeError,
    IngestEnvelopeSource,
    ingest_directory,
    _parse_envelope,
)


FIXTURE = Path(__file__).parent / "fixtures" / "envelope_v1_1.json"


# ── Parser unit tests ─────────────────────────────────────────────────


def test_parse_envelope_protocol_1_1_ok():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    src, decisions, drift = _parse_envelope(payload)
    assert src == IngestEnvelopeSource(
        app_id="keti-veritas-test",
        app_type="video_forensics",
        instance_id=None,
    )
    assert len(decisions) == 3
    assert {d.decision_type for d in decisions} == {
        "tessera_match", "detection_accept", "continuous_eval",
    }
    assert drift is None


def test_parse_envelope_unsupported_protocol_rejects():
    with pytest.raises(EnvelopeError, match="protocol_version"):
        _parse_envelope({"protocol_version": "0.9", "source": {"app_id": "x"}, "payload_kinds": []})


def test_parse_envelope_missing_source_rejects():
    with pytest.raises(EnvelopeError, match="source.app_id"):
        _parse_envelope({"protocol_version": "1.1", "payload_kinds": []})


def test_parse_envelope_drift_only_no_decisions():
    payload = {
        "protocol_version": "1.1",
        "source": {"app_id": "site-a"},
        "payload_kinds": ["drift_report"],
        "drift_report": {"severity": "medium", "scores": {"overall": 0.42}},
    }
    src, decisions, drift = _parse_envelope(payload)
    assert src.app_id == "site-a"
    assert decisions == []
    assert drift == {"severity": "medium", "scores": {"overall": 0.42}}


# ── Directory ingest integration tests ───────────────────────────────


def test_ingest_directory_round_trip(tmp_path):
    """Drop fixture into export dir, ingest, check inbox + processed."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    target = export_dir / "decision_batch_20260507T080030Z_3.json"
    shutil.copy(FIXTURE, target)

    workspace = tmp_path / "ws"
    outcome = ingest_directory(
        from_dir=export_dir,
        workspace_root=workspace,
    )

    assert outcome.site_id == "keti-veritas-test"
    assert outcome.files_seen == 1
    assert outcome.files_processed == 1
    assert outcome.files_skipped == []
    assert outcome.decision_rows == 3
    assert outcome.drift_reports == 0

    # Decisions CSV exists with header + 3 rows
    csv_path = Path(outcome.decisions_path)
    assert csv_path.exists()
    with csv_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3
    assert rows[0]["decision_type"] == "tessera_match"
    assert rows[0]["site_id"] == "keti-veritas-test"
    assert rows[0]["source_file"] == "decision_batch_20260507T080030Z_3.json"
    # Nested fields are JSON-encoded strings
    assert json.loads(rows[0]["scores_json"]) == {
        "clip": 0.82, "dinov2": 0.74, "fingerprint": 0.91,
    }

    # Manifest line written
    manifest = Path(outcome.manifest_path)
    assert manifest.exists()
    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["decision_rows"] == 3

    # Source moved to .processed/
    processed = workspace / ".ddoc" / "inbox" / "keti-veritas-test" / ".processed"
    assert (processed / target.name).exists()
    assert not target.exists()  # original gone


def test_ingest_directory_idempotent_rerun(tmp_path):
    """Second run on same export dir is a no-op (files already in .processed/)."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    shutil.copy(FIXTURE, export_dir / "env.json")

    workspace = tmp_path / "ws"
    first = ingest_directory(from_dir=export_dir, workspace_root=workspace)
    assert first.files_processed == 1

    # second pass — export_dir is now empty (file moved to .processed/)
    second = ingest_directory(from_dir=export_dir, workspace_root=workspace)
    assert second.files_seen == 0
    assert second.files_processed == 0
    assert second.decision_rows == 0


def test_ingest_directory_explicit_site_id_override(tmp_path):
    """--site-id flag overrides envelope's source.app_id for routing."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    shutil.copy(FIXTURE, export_dir / "env.json")

    workspace = tmp_path / "ws"
    outcome = ingest_directory(
        from_dir=export_dir,
        workspace_root=workspace,
        site_id="custom-site",
    )
    assert outcome.site_id == "custom-site"
    assert (workspace / ".ddoc" / "inbox" / "custom-site").exists()
    # envelope's app_id is NOT used as a directory
    assert not (workspace / ".ddoc" / "inbox" / "keti-veritas-test").exists()


def test_ingest_directory_delete_mode(tmp_path):
    """mode=delete removes source files instead of moving."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    target = export_dir / "env.json"
    shutil.copy(FIXTURE, target)

    workspace = tmp_path / "ws"
    outcome = ingest_directory(
        from_dir=export_dir,
        workspace_root=workspace,
        mode="delete",
    )
    assert outcome.files_processed == 1
    assert not target.exists()
    processed = workspace / ".ddoc" / "inbox" / "keti-veritas-test" / ".processed"
    assert not processed.exists() or list(processed.iterdir()) == []


def test_ingest_directory_skips_malformed(tmp_path):
    """Malformed envelopes are reported in skipped, not crashed."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    # valid
    shutil.copy(FIXTURE, export_dir / "good.json")
    # invalid: not JSON
    (export_dir / "bad_invalid.json").write_text("not json", encoding="utf-8")
    # invalid: protocol mismatch
    (export_dir / "bad_proto.json").write_text(json.dumps({
        "protocol_version": "0.9", "source": {"app_id": "x"}, "payload_kinds": [],
    }), encoding="utf-8")

    workspace = tmp_path / "ws"
    outcome = ingest_directory(from_dir=export_dir, workspace_root=workspace)
    assert outcome.files_seen == 3
    assert outcome.files_processed == 1  # only the valid one
    assert len(outcome.files_skipped) == 2
    skipped_files = {s["file"] for s in outcome.files_skipped}
    assert skipped_files == {"bad_invalid.json", "bad_proto.json"}


def test_ingest_drift_report_only(tmp_path):
    """Envelope with only drift_report payload writes sidecar JSON, no CSV."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    drift_only = {
        "protocol_version": "1.1",
        "source": {"app_id": "site-d"},
        "payload_kinds": ["drift_report"],
        "drift_report": {"severity": "high", "scores": {"overall": 0.71}},
        "sent_at": "2026-05-07T09:00:00+00:00",
    }
    (export_dir / "drift.json").write_text(json.dumps(drift_only), encoding="utf-8")

    workspace = tmp_path / "ws"
    outcome = ingest_directory(from_dir=export_dir, workspace_root=workspace)
    assert outcome.files_processed == 1
    assert outcome.decision_rows == 0
    assert outcome.drift_reports == 1
    assert outcome.decisions_path is None  # no CSV when no decisions
    assert len(outcome.drift_paths) == 1
    drift_doc = json.loads(Path(outcome.drift_paths[0]).read_text(encoding="utf-8"))
    assert drift_doc["report"]["severity"] == "high"
    assert drift_doc["site_id"] == "site-d"


def test_ingest_empty_dir_returns_clean(tmp_path):
    workspace = tmp_path / "ws"
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    outcome = ingest_directory(from_dir=export_dir, workspace_root=workspace)
    assert outcome.files_seen == 0
    assert outcome.files_processed == 0
    assert outcome.decision_rows == 0


def test_ingest_invalid_mode_rejects(tmp_path):
    workspace = tmp_path / "ws"
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    with pytest.raises(ValueError, match="mode"):
        ingest_directory(from_dir=export_dir, workspace_root=workspace, mode="bogus")
