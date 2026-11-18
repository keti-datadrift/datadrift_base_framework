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
    # R-D4 (2026-05-19) — inline cfg mode. When set, the server
    # materializes the cfg into temp `distributions[_series].json`
    # files under a scratch dir and runs CLI path-mode on top. Moves
    # what HTTP clients used to do client-side into the server, so
    # cross-container HTTP works without shared volumes. Recognized
    # keys (delegated to whichever plugin claims `detector`):
    #   baseline_categorical / current_categorical                (R26-A plugin)
    #   baseline_categorical_series / current_categorical_series   (R33 plugin)
    cfg: Optional[Dict[str, Any]] = None
    # common
    detector: str = "default"
    quiet: bool = True
    with_embeddings: bool = False
    fusion: str = "none"
    fusion_weights: Optional[str] = None
    timeout_sec: float = 600.0


# ── /report ──────────────────────────────────────────────────────────


class ReportRenderRequest(BaseModel):
    """Render a drift / EDA envelope to a report file.

    Two modes supported (Round 25 — added inline mode for HTTP
    consumers without shared filesystem):

    * **Path mode** (original): set ``input`` and ``out`` to filesystem
      paths. The server runs the CLI, server returns the JSON
      envelope from the CLI's ``--json``.
    * **Inline mode**: set ``envelope`` (the JSON dict) and leave
      ``out`` unset → server writes the envelope to a temp file,
      runs the CLI, and streams the rendered file back as the HTTP
      response body (Content-Type matching ``format``). For HTTP-only
      consumers like ``drift_studio/backend``.
    """
    input: Optional[str] = Field(
        None, description="Path to a drift / EDA envelope JSON (path mode).",
    )
    envelope: Optional[Dict[str, Any]] = Field(
        None, description="Inline drift / EDA envelope (inline mode, Round 25).",
    )
    out: Optional[str] = Field(
        None, description="Output report path (path mode). Omit for streamed bytes.",
    )
    format: Optional[str] = Field(
        None, description="html | pdf | md. Required in inline mode (no out suffix to infer from).",
    )
    title: Optional[str] = None
    timeout_sec: float = 120.0


# ── /export ──────────────────────────────────────────────────────────


class ExportDriftReportRequest(BaseModel):
    input: str = Field(..., description="Drift envelope JSON path.")
    target: str = Field(..., description="http | file (built-in) or any plugin-registered target.")
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


# ── /recipe (Round 17) ───────────────────────────────────────────────


class RecipeBody(BaseModel):
    """One of ``yaml`` (inline YAML text) or ``path`` (file path on the
    server) is required."""
    yaml: Optional[str] = Field(default=None, description="Inline YAML text.")
    path: Optional[str] = Field(default=None, description="Server-side path to a recipe YAML file.")
    dry_run: bool = Field(default=False, description="Parse + substitute argv but skip subprocess execution.")
