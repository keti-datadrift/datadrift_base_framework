"""Drift analysis command.

Two input modes (Phase 3 — orchestrator pivot):

1. **Snapshot mode** (legacy / interactive): pass two snapshot IDs or
   aliases as positional arguments. The CLI resolves snapshots, loads
   the per-snapshot analysis cache, and feeds plugins.
2. **Path mode** (Phase 3 / backend orchestrator): pass
   ``--data-path-ref`` and ``--data-path-cur`` to skip snapshot/cache
   resolution entirely. Plugins receive the paths directly. Used by the
   drift_studio backend when it subprocess-invokes ddoc instead of
   importing ``run_drift`` as a library.

When ``--json`` is set the merged plugin result is printed to stdout as
a single JSON object (no rich formatting). Errors also use stdout JSON
in this mode for machine-parsable diagnostics.
"""
import json
import sys
import typer
from rich import print as rprint
from typing import Optional

from ..utils import get_pmgr, _pretty
from ddoc.core.snapshot_service import get_snapshot_service
from ddoc.core.cache_service import get_cache_service


def _emit(res: dict, json_out: bool) -> None:
    """Stdout writer — JSON envelope when --json, rich pretty otherwise."""
    if json_out:
        sys.stdout.write(json.dumps(res, ensure_ascii=False, default=str))
        sys.stdout.write("\n")
        sys.stdout.flush()
    else:
        rprint(_pretty(res))


def _emit_error(message: str, *, code: str, json_out: bool) -> None:
    if json_out:
        sys.stdout.write(json.dumps(
            {"status": "error", "error_code": code, "message": message},
            ensure_ascii=False,
        ))
        sys.stdout.write("\n")
        sys.stdout.flush()
    else:
        rprint(f"[red]❌ {message}[/red]")


class _StdoutToStderr:
    """Context manager that redirects ``sys.stdout`` writes to
    ``sys.stderr`` for the duration of a block.

    Used in ``--json`` mode around plugin hook invocations so that any
    ``print()`` the plugin emits doesn't pollute stdout (which is
    reserved for the final ``--json`` envelope). The plugin output is
    not lost — it surfaces on stderr, alongside NDJSON progress, where
    a backend orchestrator's ``_try_parse_last_json_object`` won't be
    confused by it.

    Round-7 (2026-05-08) — added after the audio path-mode smoke
    showed plugins' "⚠️ Skipping ..." banners leaking onto stdout in
    ``--json`` mode, breaking strict JSON parsers.
    """

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self._saved = None

    def __enter__(self):
        if self.enabled:
            self._saved = sys.stdout
            sys.stdout = sys.stderr
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.enabled and self._saved is not None:
            sys.stdout = self._saved


class _SilencePluginIO:
    """Round-9 — context manager that fully suppresses plugin stdout
    AND stderr noise during hook invocation.

    Two modes (mutually exclusive):

    * ``quiet=True``: plugin's stdout AND stderr → ``os.devnull``.
      Plugin banners and per-record diagnostics are completely silent.
      The CLI's own NDJSON progress lines on stderr are emitted
      *outside* this context (around the ``with`` block) so they
      survive — only the plugin call window is muted.
    * ``json_out=True, quiet=False``: stdout → stderr (legacy
      ``_StdoutToStderr`` behaviour); stderr untouched. Plugin output
      stays visible alongside NDJSON for diagnostics.
    * default: pass-through.
    """

    def __init__(self, *, json_out: bool, quiet: bool):
        self.json_out = json_out
        self.quiet = quiet
        self._saved_stdout = None
        self._saved_stderr = None
        self._devnull = None

    def __enter__(self):
        if self.quiet:
            import os
            self._devnull = open(os.devnull, "w")
            self._saved_stdout = sys.stdout
            self._saved_stderr = sys.stderr
            sys.stdout = self._devnull
            sys.stderr = self._devnull
        elif self.json_out:
            self._saved_stdout = sys.stdout
            sys.stdout = sys.stderr
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.quiet:
            if self._saved_stdout is not None:
                sys.stdout = self._saved_stdout
            if self._saved_stderr is not None:
                sys.stderr = self._saved_stderr
            if self._devnull is not None:
                try:
                    self._devnull.close()
                except Exception:
                    pass
        elif self.json_out and self._saved_stdout is not None:
            sys.stdout = self._saved_stdout


def emit_progress(
    progress: float,
    stage: str,
    message: str = "",
    *,
    enabled: bool = False,
) -> None:
    """Emit one NDJSON progress line on stderr (Phase 6 — orchestrator).

    Schema (per `_specs/ddoc_orchestrator_pattern.md`):
        {"progress": 0.0..1.0, "stage": "<short id>", "message": "..."}

    Stderr is the channel because stdout is reserved for the final
    ``--json`` envelope. ``enabled=False`` makes this a no-op so callers
    can sprinkle invocations unconditionally.
    """
    if not enabled:
        return
    try:
        line = json.dumps(
            {"progress": float(progress), "stage": stage, "message": message},
            ensure_ascii=False,
        )
    except (TypeError, ValueError):
        return
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def _validate_detector_against_registry(detector: str, json_out: bool) -> None:
    """Round-13 (Gap 5) — sanity-check ``--detector`` against the
    detector preset registry (``ddoc_supported_detectors`` hook) before
    forking the plugins.

    Plugins that don't implement the registry hook are silently skipped
    (their per-plugin runtime validation from Round-11/12 still catches
    bad inputs). When at least one plugin advertises the strategy, we
    pass through. When *every* responding plugin says no, we fail fast
    with a single error envelope listing the union of supported names.
    """
    if not detector or detector.lower() == "default":
        return
    pm = get_pmgr().pm
    try:
        decls = pm.hook.ddoc_supported_detectors()
    except Exception:
        return  # registry hook unavailable — defer to per-plugin check
    decls = [d for d in (decls or []) if isinstance(d, dict) and d.get("supported")]
    if not decls:
        return
    supported_union: set = set()
    for d in decls:
        supported_union.update(s.lower() for s in d.get("supported", []))
    if detector.lower() in supported_union:
        return  # at least one plugin honours it
    by_modality = {d.get("modality", "?"): sorted(d.get("supported", [])) for d in decls}
    _emit_error(
        (
            f"detector {detector!r} is not advertised by any installed plugin. "
            f"Per modality: {by_modality}. Use ``ddoc plugin detectors`` for the "
            "current registry."
        ),
        code="unsupported_detector",
        json_out=json_out,
    )
    raise typer.Exit(code=2)


def _parse_fusion_weights(spec: Optional[str]) -> dict:
    """Parse a weights spec string ``"image=0.6,text=0.4"`` into a dict.

    Empty / None returns ``{}`` (callers default to equal weights).
    Malformed entries surface as ``BadParameter`` so the CLI exits
    early rather than computing a silently wrong fusion.
    """
    if not spec:
        return {}
    out: dict = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise typer.BadParameter(
                f"--fusion-weights expects key=value pairs, got {item!r}"
            )
        k, v = item.split("=", 1)
        k = k.strip()
        try:
            out[k] = float(v.strip())
        except ValueError:
            raise typer.BadParameter(
                f"--fusion-weights value for {k!r} must be numeric, got {v!r}"
            )
    return out


def _apply_fusion(merged: dict, strategy: str, weights: dict) -> dict:
    """Compute ``fused_score`` across the per-modality results and
    annotate ``merged`` in place. Only fires when ``strategy != "none"``
    and at least 2 successful modality results are present."""
    successes = {
        m: r for m, r in merged["modalities"].items()
        if isinstance(r, dict) and r.get("status") != "error" and "overall_score" in r
    }
    if strategy == "none" or len(successes) < 2:
        return merged

    scores = {m: float(r["overall_score"]) for m, r in successes.items()}

    fusion_warnings: list = []
    if strategy == "joint":
        clamped = {}
        for m, s in scores.items():
            if s > 1.0:
                fusion_warnings.append(
                    f"modality {m!r} score {s:.4f} > 1.0; clamped for joint fusion"
                )
                clamped[m] = 1.0
            elif s < 0.0:
                clamped[m] = 0.0
            else:
                clamped[m] = s
        prod = 1.0
        for m in clamped:
            prod *= (1.0 - clamped[m])
        fused = 1.0 - prod
        applied_weights = {m: 1.0 for m in scores}
    elif strategy == "max":
        fused = max(scores.values())
        applied_weights = {m: 0.0 for m in scores}
        max_modality = max(scores, key=lambda m: scores[m])
        applied_weights[max_modality] = 1.0
    elif strategy == "weighted":
        if weights:
            unknown = set(weights) - set(scores)
            if unknown:
                fusion_warnings.append(
                    f"--fusion-weights contained unknown modalities {sorted(unknown)}; ignored"
                )
            applied = {m: float(weights.get(m, 0.0)) for m in scores}
            total = sum(applied.values())
            if total <= 0:
                fusion_warnings.append(
                    "no positive weight matched a present modality; "
                    "falling back to equal weights"
                )
                applied = {m: 1.0 / len(scores) for m in scores}
                total = 1.0
            applied_weights = {m: applied[m] / total for m in scores}
        else:
            applied_weights = {m: 1.0 / len(scores) for m in scores}
        fused = sum(applied_weights[m] * scores[m] for m in scores)
    else:
        raise typer.BadParameter(
            f"--fusion expects one of {{none,weighted,max,joint}}, got {strategy!r}"
        )

    merged["fused_score"] = float(fused)
    merged["fusion_strategy"] = strategy
    merged["fusion_weights"] = applied_weights
    merged["fusion_inputs"] = scores
    if fusion_warnings:
        merged["fusion_warnings"] = fusion_warnings
    return merged


def _merge_plugin_results(
    valid_results: list,
    hook_name: str,
    *,
    fusion: str = "none",
    fusion_weights: Optional[dict] = None,
) -> dict:
    """Collapse multi-plugin output into a single dict.

    Round-12 (Track B Gap 3 closure) — added ``fusion`` parameter so
    the CLI can compute a single combined score across modalities. The
    single-modality hoist still applies when there's effectively one
    plugin returning a useful result. Multi-modality + ``fusion="none"``
    keeps the historical stacked shape.
    """
    merged: dict = {"status": "success", "modalities": {}, "summary": {}}
    pmgr = get_pmgr()
    for i, result in enumerate(valid_results):
        if not isinstance(result, dict):
            continue
        modality = result.get("modality")
        if not modality:
            try:
                hook_impls = getattr(pmgr.pm.hook, hook_name).get_hookimpls()
                if i < len(hook_impls):
                    plugin_name = pmgr.pm.get_name(hook_impls[i].plugin)
                    name = plugin_name.lower()
                    if "vision" in name:
                        modality = "image"
                    elif "text" in name:
                        modality = "text"
                    elif "timeseries" in name or "ts" in name:
                        modality = "timeseries"
                    elif "audio" in name:
                        modality = "audio"
                    else:
                        modality = f"unknown_{i}"
                else:
                    modality = f"unknown_{i}"
            except Exception:
                modality = f"unknown_{i}"
        merged["modalities"][modality] = result
        if "summary" in result:
            merged["summary"][modality] = result["summary"]
    if len(merged["modalities"]) == 1:
        only = next(iter(merged["modalities"].values()))
        return only

    return _apply_fusion(merged, fusion, fusion_weights or {})


def analyze_drift_command(
    baseline: Optional[str] = typer.Argument(
        None, help="Baseline snapshot ID or alias (omit when using --data-path-ref)"
    ),
    current: Optional[str] = typer.Argument(
        None, help="Current snapshot ID or alias (omit when using --data-path-cur)"
    ),
    detector: str = typer.Option(
        "default", "--detector",
        help=(
            "Drift detector strategy. Round-11 (Track B) wired this through "
            "to the plugin. ``default`` (the default) keeps each plugin's "
            "historical behaviour (vision: ensemble, text: cosine, "
            "audio: wasserstein, timeseries: attributes). Explicit values: "
            "vision supports {ensemble,mmd,mean_shift,wasserstein,psi,cosine}; "
            "text {cosine}; audio {wasserstein}; timeseries {attributes}. "
            "Unsupported values produce an unsupported_detector error envelope."
        ),
    ),
    data_path_ref: Optional[str] = typer.Option(
        None, "--data-path-ref",
        help="Skip snapshot/cache; pass baseline data path directly (orchestrator mode).",
    ),
    data_path_cur: Optional[str] = typer.Option(
        None, "--data-path-cur",
        help="Skip snapshot/cache; pass current data path directly (orchestrator mode).",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON envelope to stdout (no rich formatting).",
    ),
    ndjson_progress: bool = typer.Option(
        False, "--ndjson-progress",
        help="Emit NDJSON progress lines on stderr (orchestrator streaming).",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Silence all plugin stdout/stderr during hook invocation. CLI's own NDJSON progress (if --ndjson-progress) and final --json envelope still emit.",
    ),
    with_embeddings: bool = typer.Option(
        False, "--with-embeddings",
        help="Round-10: in path mode, ask plugins to compute embeddings inline (e.g. text plugin will load CLIP) instead of falling back to attribute-only drift. Slower; requires the plugin's embedding deps (torch + CLIP for text/vision).",
    ),
    fusion: str = typer.Option(
        "none", "--fusion",
        help="Round-12: combine multi-modality results into a single fused_score. Strategies: none (default — keep stacked shape), weighted (Σ wᵢ·scoreᵢ), max (most pessimistic), joint (1-∏(1-scoreᵢ); requires bounded ∈[0,1]). Single-modality runs ignore this flag.",
    ),
    fusion_weights: Optional[str] = typer.Option(
        None, "--fusion-weights",
        help="Per-modality weights for --fusion weighted, e.g. 'image=0.6,text=0.4'. Missing modalities default to 0; total is normalized internally.",
    ),
):
    """Detect drift between two snapshots or two data paths.

    Two input modes:
      * Snapshot: ``ddoc analyze drift v01 v02``
      * Path:     ``ddoc analyze drift --data-path-ref /a --data-path-cur /b``

    Examples:
        ddoc analyze drift baseline v05
        ddoc analyze drift v01 v02 --json
        ddoc analyze drift --data-path-ref /data/a --data-path-cur /data/b --json
    """
    # ── Mode resolution ──
    path_mode = bool(data_path_ref or data_path_cur)
    if path_mode and not (data_path_ref and data_path_cur):
        _emit_error(
            "path mode requires both --data-path-ref and --data-path-cur",
            code="path_mode_incomplete", json_out=json_out,
        )
        raise typer.Exit(code=2)
    if not path_mode and not (baseline and current):
        _emit_error(
            "snapshot mode requires both baseline and current arguments "
            "(or use --data-path-ref/--data-path-cur for path mode)",
            code="snapshot_mode_incomplete", json_out=json_out,
        )
        raise typer.Exit(code=2)

    # Round-13 (Gap 5) — fail fast if --detector isn't advertised by
    # any plugin's supported-detectors registry. This complements the
    # per-plugin runtime checks in Round-11/12: catches typos before the
    # fork and gives a single consolidated error envelope.
    _validate_detector_against_registry(detector, json_out=json_out)

    # Path mode: skip snapshot resolution entirely.
    if path_mode:
        emit_progress(0.05, "start", "drift path mode init", enabled=ndjson_progress)
        if not json_out:
            rprint(f"[cyan]🔍 Drift Analysis (path mode)[/cyan]")
            rprint(f"   Ref:  {data_path_ref}")
            rprint(f"   Cur:  {data_path_cur}\n")
        cfg = {
            # No cache — caller is the orchestrator, expected to manage caching outside.
            "baseline_cache": None,
            "current_cache": None,
            "baseline_metadata": None,
            "current_metadata": None,
            # Round-10 — opt-in for plugins to compute embeddings
            # inline in path mode (otherwise drift falls back to
            # attribute-only). Only the text/vision plugins honour it.
            "with_embeddings": with_embeddings,
        }
        emit_progress(0.2, "plugin_call", "invoking drift_detect hook",
                      enabled=ndjson_progress)
        try:
            with _SilencePluginIO(json_out=json_out, quiet=quiet):
                hook_results = get_pmgr().hook.drift_detect(
                    snapshot_id_ref="__path__",
                    snapshot_id_cur="__path__",
                    data_path_ref=data_path_ref,
                    data_path_cur=data_path_cur,
                    data_hash_ref="",
                    data_hash_cur="",
                    detector=detector,
                    cfg=cfg,
                    output_path=f"analysis/drift_path_{detector}",
                )
        except Exception as e:
            _emit_error(f"plugin invocation failed: {e}", code="plugin_error", json_out=json_out)
            raise typer.Exit(code=1)
        emit_progress(0.9, "merge", "merging plugin results",
                      enabled=ndjson_progress)
        result = _finish_drift(
            hook_results, json_out=json_out,
            fusion=fusion, fusion_weights=_parse_fusion_weights(fusion_weights),
        )
        emit_progress(1.0, "complete", "done", enabled=ndjson_progress)
        return result

    # ── Snapshot mode (legacy interactive path) ──
    snapshot_service = get_snapshot_service()
    cache_service = get_cache_service()

    baseline_id = snapshot_service._resolve_version(baseline)
    current_id = snapshot_service._resolve_version(current)

    if not baseline_id:
        _emit_error(f"Snapshot '{baseline}' not found", code="snapshot_not_found", json_out=json_out)
        raise typer.Exit(code=1)
    if not current_id:
        _emit_error(f"Snapshot '{current}' not found", code="snapshot_not_found", json_out=json_out)
        raise typer.Exit(code=1)

    snap_baseline = snapshot_service._load_snapshot(baseline_id)
    snap_current = snapshot_service._load_snapshot(current_id)

    if not snap_baseline:
        _emit_error(f"Failed to load snapshot {baseline_id}", code="snapshot_load_failed", json_out=json_out)
        raise typer.Exit(code=1)
    if not snap_current:
        _emit_error(f"Failed to load snapshot {current_id}", code="snapshot_load_failed", json_out=json_out)
        raise typer.Exit(code=1)

    # Cache lookup must accept modality-suffixed cache types
    # (``attributes_timeseries`` / ``attributes_image`` / …) — plugins
    # write those, not the bare ``attributes`` key, so the legacy single-
    # type lookup quietly produced ``cache_missing`` even after a
    # successful EDA. ``find_attribute_caches`` returns every variant on
    # disk; we pick generic first if present, otherwise the first
    # available modality.
    def _pick_attr_cache(snapshot_id: str, data_hash: str):
        caches = cache_service.find_attribute_caches(
            snapshot_id=snapshot_id, data_hash=data_hash,
        )
        if not caches:
            return None
        return caches.get("attributes") or next(iter(caches.values()))

    cache_baseline_attr = _pick_attr_cache(baseline_id, snap_baseline.data.dvc_hash)
    cache_current_attr = _pick_attr_cache(current_id, snap_current.data.dvc_hash)

    if not cache_baseline_attr:
        _emit_error(
            f"No analysis cache for {baseline_id} — run 'ddoc analyze eda {baseline_id}' first",
            code="cache_missing", json_out=json_out,
        )
        raise typer.Exit(code=1)
    if not cache_current_attr:
        _emit_error(
            f"No analysis cache for {current_id} — run 'ddoc analyze eda {current_id}' first",
            code="cache_missing", json_out=json_out,
        )
        raise typer.Exit(code=1)

    cfg = {
        "baseline_cache": cache_baseline_attr,
        "current_cache": cache_current_attr,
        "baseline_metadata": cache_service.load_file_metadata(
            snapshot_id=baseline_id, data_hash=snap_baseline.data.dvc_hash,
        ),
        "current_metadata": cache_service.load_file_metadata(
            snapshot_id=current_id, data_hash=snap_current.data.dvc_hash,
        ),
        "with_embeddings": with_embeddings,
    }

    output_path = f"analysis/drift_{baseline_id}_{current_id}"

    if not json_out:
        rprint(f"[cyan]🔍 Drift Analysis[/cyan]")
        rprint(f"   Baseline: {baseline_id} ({snap_baseline.data.dvc_hash[:7]})")
        rprint(f"   Current:  {current_id} ({snap_current.data.dvc_hash[:7]})\n")

    emit_progress(0.2, "plugin_call", "invoking drift_detect hook",
                  enabled=ndjson_progress)
    try:
        with _SilencePluginIO(json_out=json_out, quiet=quiet):
            hook_results = get_pmgr().hook.drift_detect(
                snapshot_id_ref=baseline_id,
                snapshot_id_cur=current_id,
                data_path_ref=snap_baseline.data.path,
                data_path_cur=snap_current.data.path,
                data_hash_ref=snap_baseline.data.dvc_hash,
                data_hash_cur=snap_current.data.dvc_hash,
                detector=detector,
                cfg=cfg,
                output_path=output_path,
            )
    except Exception as e:
        _emit_error(f"plugin invocation failed: {e}", code="plugin_error", json_out=json_out)
        raise typer.Exit(code=1)

    emit_progress(0.9, "merge", "merging plugin results",
                  enabled=ndjson_progress)
    result = _finish_drift(
        hook_results, json_out=json_out,
        fusion=fusion, fusion_weights=_parse_fusion_weights(fusion_weights),
    )
    emit_progress(1.0, "complete", "done", enabled=ndjson_progress)
    return result


def _finish_drift(
    hook_results,
    *,
    json_out: bool,
    fusion: str = "none",
    fusion_weights: Optional[dict] = None,
) -> None:
    """Shared post-hook handling (used by both modes)."""
    if not hook_results:
        _emit_error(
            "No plugin available for drift detection. Install via: pip install ddoc-full",
            code="no_plugin", json_out=json_out,
        )
        raise typer.Exit(code=1)

    valid = [r for r in hook_results if r is not None]
    if not valid:
        _emit_error(
            "No plugin returned a valid drift result.",
            code="empty_result", json_out=json_out,
        )
        raise typer.Exit(code=1)

    res = _merge_plugin_results(
        valid, hook_name="drift_detect",
        fusion=fusion, fusion_weights=fusion_weights,
    )
    _emit(res, json_out=json_out)
