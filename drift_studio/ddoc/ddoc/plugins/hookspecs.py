# ddoc/plugins/hookspecs.py
"""
Hook specifications for ddoc plugin system with version tag.
"""
import pluggy
from typing import Any, Dict, Optional, List # List 타입 임포트 추가

hookspec = pluggy.HookspecMarker("ddoc")
hookimpl = pluggy.HookimplMarker("ddoc") 

# Bump this if you change HookSpec signatures in a breaking way.
HOOKSPEC_VERSION = "1.0.0"

# --- MLOps Core Operations (Implemented by ddoc/core/ops.py) ---

@hookspec
def data_add(name: str, config: str) -> Optional[Dict[str, Any]]:
    """Registers a new dataset version (dvc add, git branch/commit, params update)."""
    
@hookspec
def exp_run(name: str, params: str, dry_run: bool) -> Optional[Dict[str, Any]]:
    """Updates params.yaml and executes dvc exp run."""
    
@hookspec
def exp_show(name: Optional[str], baseline: Optional[str]) -> Optional[Dict[str, Any]]:
    """Shows DVC experiment results, optionally comparing two versions."""

# --- Analytical Operations (Implemented by external plugins) ---

@hookspec
def eda_run(
    snapshot_id: str,
    data_path: str,
    data_hash: str,
    output_path: str,
    invalidate_cache: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Run EDA analysis on a snapshot.
    
    Args:
        snapshot_id: Snapshot ID (or "workspace" for current workspace)
        data_path: Path to data directory
        data_hash: DVC hash of the data
        output_path: Path to save analysis results
        invalidate_cache: Whether to invalidate existing cache
        
    Returns:
        Dictionary with analysis summary
    """

@hookspec
def transform_apply(input_path: str, transform: str, args: Dict[str, Any], output_path: str) -> Optional[Dict[str, Any]]:
    """Apply a named transform and write result to output_path."""

@hookspec
def drift_detect(
    snapshot_id_ref: str,
    snapshot_id_cur: str,
    data_path_ref: str,
    data_path_cur: str,
    data_hash_ref: str,
    data_hash_cur: str,
    detector: str,
    cfg: Dict[str, Any],
    output_path: str
) -> Optional[Dict[str, Any]]:
    """
    Detect drift between two snapshots.
    
    Args:
        snapshot_id_ref: Reference snapshot ID
        snapshot_id_cur: Current snapshot ID
        data_path_ref: Reference snapshot data path
        data_path_cur: Current snapshot data path
        data_hash_ref: Reference snapshot data hash
        data_hash_cur: Current snapshot data hash
        detector: Drift detector method (e.g., "mmd")
        cfg: Configuration dictionary
        output_path: Path to save drift analysis results
        
    Returns:
        Dictionary with drift metrics
    """

@hookspec
def reconstruct_apply(input_path: str, method: str, args: Dict[str, Any], output_path: str) -> Optional[Dict[str, Any]]:
    """Reconstruct/Impute/Resample data and write result."""

@hookspec
def retrain_run(train_path: str, trainer: str, params: Dict[str, Any], model_out: str) -> Optional[Dict[str, Any]]:
    """Retrain model and write model artifact."""

@hookspec
def monitor_run(source: str, mode: str, schedule: Optional[str]) -> Optional[Dict[str, Any]]:
    """Run monitors once or on schedule."""

@hookspec
def vis_run() -> Optional[Dict[str, Any]]:
    """Run monitors once or on schedule."""


# --- Detector Preset Registry (Round-13 / Gap 5) ---


@hookspec
def ddoc_supported_detectors() -> Optional[Dict[str, Any]]:
    """Plugin self-declares the detector strategies it supports.

    Round-13 (Gap 5 from ``_specs/embedding_drift_design.md``) — closes
    the gap evidently.ai-style detector configurability covers
    naturally. Plugins return:

        {
            "modality": "image",
            "default": "ensemble",
            "supported": ["ensemble", "mmd", "cosine", ...],
            "notes": "free-form description / threshold knobs",
        }

    The CLI's ``ddoc analyze drift`` collects all plugin responses
    upfront (``ddoc plugin detectors`` exposes the same listing) so an
    operator who passes ``--detector foo`` gets a focused error
    *before* the plugins fork rather than per-plugin
    ``unsupported_detector`` envelopes after.

    Returns ``None`` if the plugin doesn't implement the convention
    (legacy plugins continue to work — the per-plugin runtime
    validation from Round-11/12 still catches unsupported values).
    """
    ...


# --- Data Source Adapter (Round-13) ---


@hookspec(firstresult=True)
def data_source_read(
    source_uri: str,
    dest_dir: str,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Materialize a remote / abstract data source into a local
    directory ddoc plugins can analyze.

    Round-13 — opens the door for non-file-based inputs (S3, GCS, HTTP,
    Kafka, ...). The CLI's ``ddoc analyze drift`` path mode currently
    accepts only on-disk paths; this hook lets a plugin transparently
    pull data from anywhere into ``dest_dir`` first.

    Selection by URL scheme:

    * ``file://`` — built-in fallback (copy / passthrough).
    * ``s3://`` — handled by a plugin that pulls via boto3.
    * ``gs://``, ``http(s)://`` etc. — same idea, plugin per scheme.

    ``firstresult=True`` so the first plugin claiming the scheme wins;
    plugins return ``None`` for schemes they don't handle.

    Returns
    -------
    ``{status, scheme, source_uri, local_path, bytes_transferred,
    files_count}`` on success. Plugins should make ``local_path``
    pointer to the directory inside ``dest_dir`` that ddoc analyze can
    treat as a path-mode input.
    """
    ...


# --- Reporting / Export (Round-11 / Track C) ---


@hookspec(firstresult=True)
def report_render(
    drift_result: Optional[Dict[str, Any]],
    eda_result: Optional[Dict[str, Any]],
    format: str,
    output_path: str,
    cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Render a drift / EDA result to a report file.

    Round-11 (Track C) — lifts report generation from backend-internal
    (pdfkit + Jinja in ``drift_studio/backend/app/routers/report.py``)
    to a ddoc-CLI plugin-extensible hookspec. The CLI subcommand
    ``ddoc report render`` invokes this hook; if no plugin returns a
    non-None result, ``ddoc/cli/commands/report.py`` falls back to a
    built-in Jinja+weasyprint implementation.

    Parameters
    ----------
    drift_result, eda_result :
        At least one is non-None. The plugin chooses a layout per
        what's provided.
    format :
        ``"html"`` | ``"pdf"`` | ``"md"``. The plugin should return
        ``None`` (rather than error) for formats it doesn't support so
        another plugin or the built-in fallback can handle it.
    output_path :
        Final on-disk path. Plugin writes the file and returns the
        size + status.
    cfg :
        Free-form options (e.g. ``{"title": "...", "include_plots": true}``).

    Returns
    -------
    ``{status, format, output_path, size_bytes, ...}`` on success,
    ``None`` if this plugin doesn't handle the requested format.

    Note: ``firstresult=True`` — the first plugin that returns a
    non-None value wins. Operators can prioritise a custom plugin over
    the built-in fallback by ensuring its entry point loads first.
    """


@hookspec(firstresult=True)
def export_drift_report(
    drift_result: Dict[str, Any],
    target: str,
    target_config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Ship a drift report to an external system.

    Round-11 (Track C) — the reverse of ``ddoc ingest`` (which consumes
    keti_veritas envelope JSON). This hook lets ddoc emit the
    drift_result back to keti_veritas, a file system, S3, etc., using
    plugin adapters.

    Parameters
    ----------
    drift_result :
        The envelope produced by ``ddoc analyze drift``.
    target :
        Adapter selector. Built-in adapters: ``"keti_veritas"``
        (HTTP POST to ``<base_url>/field-agents/drift-report``),
        ``"file"`` (atomic JSON write into ``<out_dir>/``). Plugins
        can register additional targets (e.g. ``"s3"``,
        ``"slack"``).
    target_config :
        Adapter-specific options. ``keti_veritas``: ``{base_url,
        api_key?, timeout_sec?, source: {app_id, app_type}}``.
        ``file``: ``{out_dir, filename?}``.

    Returns
    -------
    ``{status, target, transmitted_at, response, ...}`` on success,
    ``None`` if this plugin doesn't handle the requested target so
    another plugin / built-in fallback can.
    """
    
# --- Plugin Metadata Hook (NEW) ---
@hookspec(firstresult=True)
def ddoc_get_metadata() -> Optional[Dict[str, Any]]:
    """
    Returns structured metadata (name, description, implemented hooks) 
    about the plugin.
    
    Note: firstresult=True is typically not used for gathering, but here 
    we assume the list of results is gathered elsewhere. Since the external 
    plugin returns a full dict, we keep it simple for now. 
    For listing, we gather all results manually (see cli/commands.py).
    """

# --- Plugin Metadata Hook (NEW) ---
@hookspec(firstresult=True)
def ddoc_get_metadata2() -> Optional[Dict[str, Any]]:
    """
    Returns structured metadata (name, description, implemented hooks) 
    about the plugin.
    
    Note: firstresult=True is typically not used for gathering, but here 
    we assume the list of results is gathered elsewhere. Since the external 
    plugin returns a full dict, we keep it simple for now. 
    For listing, we gather all results manually (see cli/commands.py).
    """

