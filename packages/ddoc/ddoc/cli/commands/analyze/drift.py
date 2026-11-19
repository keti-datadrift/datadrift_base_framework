"""Drift analysis command.

Pass ``--data-path-ref`` and ``--data-path-cur``; plugins receive the
paths directly. Orchestrating backends can subprocess-invoke this
instead of importing ddoc as a library.

When ``--json`` is set the merged plugin result is printed to stdout as
a single JSON object (no rich formatting). Errors also use stdout JSON
in this mode for machine-parsable diagnostics.
"""
import json
import sys
import typer
from rich import print as rprint
from typing import Optional

from ..utils import call_hook_isolated, get_pmgr, _pretty


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

    Added after the audio path-mode smoke test showed plugins'
    "⚠️ Skipping ..." banners leaking onto stdout in ``--json`` mode,
    breaking strict JSON parsers.
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
    """Context manager that fully suppresses plugin stdout
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
    """Emit one NDJSON progress line on stderr for orchestrating callers.

    Schema:
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
    """Sanity-check ``--detector`` against the
    detector preset registry (``ddoc_supported_detectors`` hook) before
    forking the plugins.

    Plugins that don't implement the registry hook are silently skipped
    (their per-plugin runtime validation elsewhere still catches
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

    Added ``fusion`` parameter so
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
    detector: str = typer.Option(
        "default", "--detector",
        help=(
            "Drift detector strategy, wired through "
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
        help="Baseline data path.",
    ),
    data_path_cur: Optional[str] = typer.Option(
        None, "--data-path-cur",
        help="Current data path.",
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
        help="Ask plugins to compute embeddings inline (e.g. text plugin will load CLIP) instead of falling back to attribute-only drift. Slower; requires the plugin's embedding deps (torch + CLIP for text/vision).",
    ),
    fusion: str = typer.Option(
        "none", "--fusion",
        help="Combine multi-modality results into a single fused_score. Strategies: none (default — keep stacked shape), weighted (Σ wᵢ·scoreᵢ), max (most pessimistic), joint (1-∏(1-scoreᵢ); requires bounded ∈[0,1]). Single-modality runs ignore this flag.",
    ),
    fusion_weights: Optional[str] = typer.Option(
        None, "--fusion-weights",
        help="Per-modality weights for --fusion weighted, e.g. 'image=0.6,text=0.4'. Missing modalities default to 0; total is normalized internally.",
    ),
):
    """Detect drift between two data paths.

    Examples:
        ddoc analyze drift --data-path-ref /data/a --data-path-cur /data/b
        ddoc analyze drift --data-path-ref /data/a --data-path-cur /data/b --json
    """
    if not (data_path_ref and data_path_cur):
        _emit_error(
            "both --data-path-ref and --data-path-cur are required",
            code="path_mode_incomplete", json_out=json_out,
        )
        raise typer.Exit(code=2)

    # Fail fast if --detector isn't advertised by
    # any plugin's supported-detectors registry. This complements the
    # per-plugin runtime checks elsewhere: catches typos before the
    # fork and gives a single consolidated error envelope.
    _validate_detector_against_registry(detector, json_out=json_out)

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
        # Opt-in for plugins to compute embeddings
        # inline in path mode (otherwise drift falls back to
        # attribute-only). Only the text/vision plugins honour it.
        "with_embeddings": with_embeddings,
    }
    emit_progress(0.2, "plugin_call", "invoking drift_detect hook",
                  enabled=ndjson_progress)
    try:
        with _SilencePluginIO(json_out=json_out, quiet=quiet):
            hook_results, hook_errors = call_hook_isolated(
                get_pmgr(), "drift_detect",
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
    if hook_errors and not hook_results:
        detail = "; ".join(f"{name}: {err}" for name, err in hook_errors)
        _emit_error(f"plugin invocation failed: {detail}", code="plugin_error", json_out=json_out)
        raise typer.Exit(code=1)
    for name, err in hook_errors:
        rprint(f"[yellow]plugin {name} failed and was skipped: {err}[/yellow]", file=sys.stderr)
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
