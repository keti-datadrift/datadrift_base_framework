"""Pydantic request models for the ``ddoc serve`` REST facade.

Every request body mirrors the corresponding ddoc CLI subcommand
options 1-to-1 — the routers translate ``Request`` instances into
argv lists for ``runner.run()``. Responses are returned as the raw
ddoc JSON envelope (``Dict[str, Any]``) since the CLI already
guarantees a stable shape per subcommand and we don't want to
double-validate.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── /examples ────────────────────────────────────────────────────────


class ExamplesGenerateRequest(BaseModel):
    modality: str = Field(..., description="One of: timeseries, audio, text, vision.")
    out: str = Field(..., description="Output directory (will contain ref/ and cur/ subdirs).")
    scenario: str = Field("shifted", description="`shifted` or `identical`.")


# ── /analyze ─────────────────────────────────────────────────────────


class AnalyzeEdaRequest(BaseModel):
    snapshot: Optional[str] = None
    data_path: Optional[str] = None
    invalidate_cache: bool = False
    save_snapshot: bool = False
    strict_hash: bool = False
    quiet: bool = True
    timeout_sec: float = 600.0


class AnalyzeDriftRequest(BaseModel):
    # path mode
    data_path_ref: Optional[str] = None
    data_path_cur: Optional[str] = None
    # snapshot mode
    baseline: Optional[str] = None
    current: Optional[str] = None
    # common
    detector: str = "default"
    quiet: bool = True
    with_embeddings: bool = False
    fusion: str = "none"
    fusion_weights: Optional[str] = None
    timeout_sec: float = 600.0


# ── /report ──────────────────────────────────────────────────────────


class ReportRenderRequest(BaseModel):
    input: str = Field(..., description="Path to a drift / EDA envelope JSON.")
    out: str = Field(..., description="Output report path.")
    format: Optional[str] = Field(
        None, description="html | pdf | md (default: inferred from --out suffix).",
    )
    title: Optional[str] = None
    timeout_sec: float = 120.0


# ── /export ──────────────────────────────────────────────────────────


class ExportDriftReportRequest(BaseModel):
    input: str = Field(..., description="Drift envelope JSON path.")
    target: str = Field(..., description="keti_veritas | file (built-in) or any plugin-registered target.")
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Adapter-specific options (passed to --config inline JSON).",
    )
    timeout_sec: float = 120.0


# ── /fetch ───────────────────────────────────────────────────────────


class FetchRequest(BaseModel):
    source_uri: str = Field(..., description="file://, bare path, s3://, gs://, http(s)://, …")
    dest: str = Field(..., description="Local directory to materialize into.")
    symlink: bool = False
    config: Optional[Dict[str, Any]] = None
    timeout_sec: float = 120.0


# ── Common envelopes ────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    ddoc_version: str
    plugin_count: int
    auth_enabled: bool
    bind: str
