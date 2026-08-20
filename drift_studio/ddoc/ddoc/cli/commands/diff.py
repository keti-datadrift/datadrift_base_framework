"""``ddoc diff`` — one-line drift verdict between two datasets.

The front door of ddoc: point it at two paths (directories or files)
and get a human verdict, not just a score.

    ddoc diff baseline_data/ todays_data/

Design goals (the "ffmpeg test"):

* **Verb** — ``diff`` is the whole mental model: what changed between
  REF and CUR?
* **Tolerance** — sniffs the input modality itself. Prepared ddoc
  layouts go through the plugin ``drift_detect`` hook; bare CSV
  files/folders fall back to a built-in comparator (pandas +
  Jensen-Shannon on per-column histograms) so the common case works
  with zero setup and zero extra plugins.
* **Verdict** — every run ends in one of ``OK`` / ``DRIFT`` /
  ``BLIND``. BLIND is a first-class answer ("cannot determine"), not
  a stack trace.
* **Pipes** — exit code carries the verdict: 0 = OK, 1 = DRIFT,
  2 = BLIND/error. ``--json`` emits exactly one JSON object on stdout.

``ddoc analyze drift`` remains the low-level instrument (detectors,
fusion, snapshots); ``diff`` is the opinionated facade over it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
from rich import print as rprint

from .utils import get_pmgr

EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_BLIND = 2

# File-extension → modality sniffing table.
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
_TEXT_EXTS = {".txt", ".md"}


# ── Sniffing ──────────────────────────────────────────────────────────


def sniff_modality(path: Path) -> Tuple[str, Dict[str, Any]]:
    """Best-effort guess of what kind of dataset ``path`` is.

    Returns ``(kind, detail)`` where kind is one of
    ``categorical | vision | audio | text | csv | unknown``.
    Layout markers win over extension counting.
    """
    if path.is_file():
        ext = path.suffix.lower()
        if ext == ".csv":
            return "csv", {"files": [str(path)]}
        if ext in _IMAGE_EXTS:
            return "vision", {"files": [str(path)]}
        if ext in _AUDIO_EXTS:
            return "audio", {"files": [str(path)]}
        if ext in _TEXT_EXTS:
            return "text", {"files": [str(path)]}
        return "unknown", {"files": [str(path)]}

    # Directory: explicit ddoc layout markers first.
    for marker in ("distributions.json", "distributions_series.json"):
        if (path / marker).is_file():
            return "categorical", {"marker": marker}

    counts: Dict[str, int] = {}
    csvs: List[str] = []
    for p in sorted(path.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        ext = p.suffix.lower()
        if ext == ".csv":
            counts["csv"] = counts.get("csv", 0) + 1
            csvs.append(str(p))
        elif ext in _IMAGE_EXTS:
            counts["vision"] = counts.get("vision", 0) + 1
        elif ext in _AUDIO_EXTS:
            counts["audio"] = counts.get("audio", 0) + 1
        elif ext in _TEXT_EXTS:
            counts["text"] = counts.get("text", 0) + 1
    if not counts:
        return "unknown", {"counts": {}}
    kind = max(counts, key=lambda k: counts[k])
    detail: Dict[str, Any] = {"counts": counts}
    if kind == "csv":
        detail["files"] = csvs
    return kind, detail


# ── Built-in CSV comparator (zero-plugin fallback) ────────────────────


def _js_divergence(p: Dict[Any, float], q: Dict[Any, float]) -> float:
    """Base-2 Jensen-Shannon divergence over aligned count dicts, ∈[0,1]."""
    import math

    keys = set(p) | set(q)
    if not keys:
        return 0.0

    def norm(d: Dict[Any, float]) -> Dict[Any, float]:
        total = sum(d.get(k, 0.0) for k in keys) or 1.0
        return {k: d.get(k, 0.0) / total for k in keys}

    pn, qn = norm(p), norm(q)
    m = {k: (pn[k] + qn[k]) / 2.0 for k in keys}

    def kl(a: Dict[Any, float], b: Dict[Any, float]) -> float:
        s = 0.0
        for k in keys:
            if a[k] > 0 and b[k] > 0:
                s += a[k] * math.log2(a[k] / b[k])
        return s

    return max(0.0, min(1.0, 0.5 * kl(pn, m) + 0.5 * kl(qn, m)))


def _load_csv_frame(files: List[str]):
    import pandas as pd

    frames = [pd.read_csv(f) for f in files]
    return pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]


def csv_diff(ref_files: List[str], cur_files: List[str], bins: int = 20) -> Dict[str, Any]:
    """Column-wise drift between two CSV datasets.

    Numeric columns → shared-range histogram JS divergence;
    non-numeric columns → value-count JS divergence.
    ``overall_score`` = mean over shared columns.
    """
    import numpy as np
    import pandas as pd

    ref, cur = _load_csv_frame(ref_files), _load_csv_frame(cur_files)
    shared = [c for c in ref.columns if c in cur.columns]
    if not shared:
        raise ValueError(
            f"no shared columns between ref {list(ref.columns)} and cur {list(cur.columns)}"
        )

    attribute_drifts: Dict[str, float] = {}
    for col in shared:
        r, c = ref[col].dropna(), cur[col].dropna()
        if r.empty and c.empty:
            continue
        if pd.api.types.is_numeric_dtype(r) and pd.api.types.is_numeric_dtype(c):
            lo = float(min(r.min(), c.min()))
            hi = float(max(r.max(), c.max()))
            if hi == lo:
                attribute_drifts[col] = 0.0
                continue
            edges = np.linspace(lo, hi, bins + 1)
            rh, _ = np.histogram(r, bins=edges)
            ch, _ = np.histogram(c, bins=edges)
            attribute_drifts[col] = _js_divergence(
                dict(enumerate(rh.tolist())), dict(enumerate(ch.tolist()))
            )
        else:
            attribute_drifts[col] = _js_divergence(
                r.astype(str).value_counts().to_dict(),
                c.astype(str).value_counts().to_dict(),
            )

    overall = sum(attribute_drifts.values()) / len(attribute_drifts) if attribute_drifts else 0.0
    return {
        "status": "success",
        "modality": "tabular",
        "detector": "builtin:csv_js",
        "overall_score": round(overall, 4),
        "attribute_drifts": {k: round(v, 4) for k, v in attribute_drifts.items()},
        "rows": {"ref": int(len(ref)), "cur": int(len(cur))},
        "columns_compared": shared,
    }


# ── Verdict ───────────────────────────────────────────────────────────


def compute_verdict(
    result: Dict[str, Any], *, threshold: float, attr_threshold: float
) -> Tuple[str, str, List[Tuple[str, float]]]:
    """Map a drift envelope to (verdict, severity, top_attributes).

    DRIFT when overall ≥ threshold OR any single attribute ≥
    attr_threshold (a strong local shift shouldn't be averaged away).
    """
    overall = float(result.get("overall_score") or 0.0)
    attrs = result.get("attribute_drifts") or {}
    top = sorted(
        ((k, float(v)) for k, v in attrs.items() if isinstance(v, (int, float))),
        key=lambda kv: kv[1], reverse=True,
    )[:5]
    max_attr = top[0][1] if top else 0.0

    if overall >= attr_threshold or max_attr >= attr_threshold:
        return "DRIFT", "high", top
    if overall >= threshold:
        return "DRIFT", "medium", top
    if overall >= threshold / 3:
        return "OK", "low", top
    return "OK", "none", top


# ── Output ────────────────────────────────────────────────────────────


def _emit_json(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def _print_human(payload: Dict[str, Any]) -> None:
    verdict = payload["verdict"]
    icon = {"OK": "[green]✅ OK[/green]",
            "DRIFT": "[red]⚠ DRIFT[/red]",
            "BLIND": "[yellow]◌ BLIND[/yellow]"}[verdict]
    head = f"{icon} — severity: {payload['severity']}"
    if payload.get("overall_score") is not None:
        head += f" · score {payload['overall_score']:.4f} (threshold {payload['threshold']})"
    rprint(head)
    if payload.get("top_attributes"):
        tops = " · ".join(f"{k} {v:.3f}" for k, v in payload["top_attributes"][:3])
        rprint(f"   가장 변한 속성: {tops}")
    rprint(f"   modality: {payload.get('modality') or '?'} · engine: {payload.get('engine')}"
           f" · ref: {payload['ref']} · cur: {payload['cur']}")
    if verdict == "BLIND":
        rprint(f"   [yellow]사유:[/yellow] {payload.get('reason')}")
    for hint in payload.get("hints", []):
        rprint(f"   ⤷ {hint}")


def _finish(payload: Dict[str, Any], *, json_out: bool) -> None:
    if json_out:
        _emit_json(payload)
    else:
        _print_human(payload)
    code = {"OK": EXIT_OK, "DRIFT": EXIT_DRIFT, "BLIND": EXIT_BLIND}[payload["verdict"]]
    raise typer.Exit(code=code)


def _blind(reason: str, *, ref: str, cur: str, json_out: bool,
           modality: Optional[str] = None, hints: Optional[List[str]] = None) -> None:
    _finish({
        "verdict": "BLIND", "severity": "unknown", "overall_score": None,
        "modality": modality, "engine": None, "detector": None,
        "ref": ref, "cur": cur, "reason": reason, "hints": hints or [],
        "top_attributes": [], "threshold": None,
    }, json_out=json_out)


# ── Command ───────────────────────────────────────────────────────────


def diff_command(
    ref: Path = typer.Argument(..., help="Baseline dataset (directory or file)."),
    cur: Path = typer.Argument(..., help="Current dataset (directory or file)."),
    threshold: float = typer.Option(
        0.15, "--threshold",
        help="Overall-score threshold for the DRIFT verdict.",
    ),
    attr_threshold: float = typer.Option(
        0.25, "--attr-threshold",
        help="Single-attribute threshold — one strongly drifted attribute "
             "triggers DRIFT even when the average looks calm.",
    ),
    detector: str = typer.Option(
        "default", "--detector",
        help="Detector passed through to plugins (see `ddoc plugin detectors`).",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit exactly one JSON verdict object on stdout.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Show plugin diagnostics instead of silencing them.",
    ),
):
    """One-line drift verdict between REF and CUR.

    Exit code carries the verdict: 0 = OK, 1 = DRIFT, 2 = BLIND/error.

    Examples:
        ddoc diff baseline_data/ todays_data/
        ddoc diff jan.csv aug.csv --json
        ddoc diff camA_ref/ camA_now/ --attr-threshold 0.3
    """
    ref_s, cur_s = str(ref), str(cur)
    for label, p in (("ref", ref), ("cur", cur)):
        if not p.exists():
            _blind(f"{label} 경로가 존재하지 않습니다: {p}",
                   ref=ref_s, cur=cur_s, json_out=json_out)

    ref_kind, ref_detail = sniff_modality(ref)
    cur_kind, cur_detail = sniff_modality(cur)
    kind = ref_kind if ref_kind == cur_kind else "mixed"

    # 1) Plugin hook first — prepared layouts get the full detector stack.
    from .analyze.drift import _SilencePluginIO, _merge_plugin_results

    result: Optional[Dict[str, Any]] = None
    engine: Optional[str] = None
    try:
        with _SilencePluginIO(json_out=True, quiet=not verbose):
            hook_results = get_pmgr().hook.drift_detect(
                snapshot_id_ref="__path__", snapshot_id_cur="__path__",
                data_path_ref=ref_s, data_path_cur=cur_s,
                data_hash_ref="", data_hash_cur="",
                detector=detector,
                cfg={"baseline_cache": None, "current_cache": None,
                     "baseline_metadata": None, "current_metadata": None,
                     "with_embeddings": False},
                output_path="analysis/diff",
            )
        valid = [r for r in (hook_results or []) if r is not None
                 and r.get("status") not in ("error", "unsupported")]
        if valid:
            result = _merge_plugin_results(valid, hook_name="drift_detect")
            engine = "plugin"
    except Exception as e:  # noqa: BLE001 — fall through to builtin/BLIND
        if verbose:
            rprint(f"[yellow]plugin hook failed: {e}[/yellow]")

    # 2) Built-in CSV fallback — the bare-folder common case.
    if result is None and kind == "csv":
        try:
            result = csv_diff(ref_detail.get("files") or [ref_s],
                              cur_detail.get("files") or [cur_s])
            engine = "builtin"
        except Exception as e:  # noqa: BLE001
            _blind(f"CSV 비교 실패: {e}", ref=ref_s, cur=cur_s,
                   json_out=json_out, modality="tabular")

    # 3) Still nothing → honest BLIND with a prescription.
    if result is None:
        hints = []
        if kind == "vision":
            hints.append("이미지 드리프트 플러그인 설치: pip install ddoc-plugin-vision (torch 필요)")
        elif kind in ("audio", "text"):
            hints.append(f"pip install ddoc-plugin-{kind}")
        elif kind == "unknown":
            hints.append("지원 입력: 이미지/오디오/텍스트 폴더, CSV, ddoc categorical 레이아웃")
        _blind(
            f"감지된 입력 종류 '{kind}' 를 처리할 엔진이 응답하지 않았습니다",
            ref=ref_s, cur=cur_s, json_out=json_out, modality=kind, hints=hints,
        )

    verdict, severity, top = compute_verdict(
        result, threshold=threshold, attr_threshold=attr_threshold,
    )
    hints: List[str] = []
    if verdict == "DRIFT":
        worst = top[0][0] if top else "?"
        hints.append(f"처방: '{worst}' 축의 최근 샘플을 재계측/재라벨 후보로 검토")
        hints.append("소견서: ddoc report render 로 근거 리포트 생성 (--json 출력 저장 후 입력으로)")

    _finish({
        "verdict": verdict,
        "severity": severity,
        "overall_score": float(result.get("overall_score") or 0.0),
        "threshold": threshold,
        "attr_threshold": attr_threshold,
        "top_attributes": top,
        "modality": result.get("modality") or kind,
        "detector": result.get("detector") or detector,
        "engine": engine,
        "ref": ref_s, "cur": cur_s,
        "hints": hints,
        "raw": result,
    }, json_out=json_out)
