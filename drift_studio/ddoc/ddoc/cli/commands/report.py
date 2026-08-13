"""``ddoc report render`` — render a drift / EDA result to a report file.

Round 11 (Track C) — first concrete user of the new ``report_render``
hookspec. The CLI:

1. Reads the ``--input`` JSON (drift or EDA envelope).
2. Tries the hookspec — if any plugin returns a non-None result, use that.
3. Falls back to a built-in Jinja+weasyprint implementation for HTML
   (and HTML→PDF) using the templates in ``ddoc/templates/``.

Markdown output is also handled by the built-in fallback (no Jinja
needed). The hookspec keeps the door open for richer plugins
(e.g., ``ddoc-plugin-report-fancy`` with charts).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich import print as rprint

from .utils import get_pmgr


def _load_input(input_path: Path) -> Dict[str, Any]:
    if not input_path.exists():
        raise typer.BadParameter(f"input file does not exist: {input_path}")
    return json.loads(input_path.read_text(encoding="utf-8"))


def _normalize_attribute_drifts(value: Any) -> list[tuple[str, Optional[float], Dict[str, Any]]]:
    """Normalize the many possible ``attribute_drifts`` shapes into a
    uniform list of ``(name, score, extras)`` tuples.

    Round 28 (Track C) — closes the markdown renderer's ``{v:.4f}``
    crash on non-flat shapes (discovered while writing Round 25 tests).
    Accepted inputs:

    * Flat dict: ``{"blur": 0.18, "exposure": 0.07}`` — original shape.
    * Nested dict: ``{"blur": {"score": 0.18, "status": "warning"}, ...}``.
    * List of dicts: ``[{"attribute": "blur", "score": 0.18,
      "status": "warning"}, ...]``.
    * Empty / None / unrecognized → ``[]`` (renderers skip the section).

    Score may be ``None`` if the source shape doesn't supply a numeric
    value; renderers should display "—" or skip in that case.
    """
    if not value:
        return []

    out: list[tuple[str, Optional[float], Dict[str, Any]]] = []

    def _coerce_score(v: Any) -> Optional[float]:
        if isinstance(v, (int, float)):
            return float(v)
        return None

    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, dict):
                score = _coerce_score(v.get("score"))
                extras = {kk: vv for kk, vv in v.items() if kk != "score"}
                out.append((str(k), score, extras))
            else:
                out.append((str(k), _coerce_score(v), {}))
        return out

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = str(
                    item.get("attribute")
                    or item.get("name")
                    or item.get("key")
                    or "?"
                )
                score = _coerce_score(item.get("score"))
                extras = {
                    k: v for k, v in item.items()
                    if k not in ("attribute", "name", "key", "score")
                }
                out.append((name, score, extras))
        return out

    return []  # unrecognized — skip the section gracefully


def _classify_envelope(payload: Dict[str, Any]) -> tuple[Optional[Dict], Optional[Dict]]:
    """Return ``(drift_result, eda_result)`` after a heuristic.

    drift envelopes carry ``modality`` + (``overall_score`` |
    ``attribute_drifts``). EDA envelopes have ``modality`` + ``summary``
    /``files_analyzed``/``series_analyzed``. When ambiguous, treat as
    drift (the more common case).
    """
    if "modalities" in payload:
        # multi-modal stacked result; pass as drift since each modality
        # is a drift result. Templates will iterate.
        return payload, None
    is_eda_shaped = (
        "files_analyzed" in payload
        or "series_analyzed" in payload
        or "texts_analyzed" in payload
        or ("summary" in payload and "overall_score" not in payload)
    )
    if is_eda_shaped:
        return None, payload
    return payload, None


def _builtin_render(
    drift_result: Optional[Dict[str, Any]],
    eda_result: Optional[Dict[str, Any]],
    fmt: str,
    output_path: str,
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """Built-in fallback renderer used when no plugin handles the
    request. HTML via Jinja (templates ship with the wheel), PDF via
    weasyprint, Markdown via inline string formatting."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "md":
        body = _render_markdown(drift_result, eda_result, cfg)
        out_path.write_text(body, encoding="utf-8")
        return {
            "status": "success",
            "format": "md",
            "output_path": str(out_path),
            "size_bytes": out_path.stat().st_size,
            "renderer": "builtin",
        }

    # HTML / PDF both go through Jinja first.
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
    if not templates_dir.exists():
        raise typer.BadParameter(
            f"built-in templates dir missing: {templates_dir} "
            "(reinstall ddoc; templates are package-data)"
        )

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    def _status_class(score: Optional[float]) -> str:
        if score is None:
            return "normal"
        if score < 0.15:
            return "normal"
        if score < 0.25:
            return "warning"
        return "critical"

    if drift_result is not None:
        tpl = env.get_template("drift_report.html")
        # Round 28 (Track C) — pre-normalize attribute_drifts so the
        # template iterates a uniform shape regardless of how the
        # producing detector serialized it.
        attr_rows = _normalize_attribute_drifts(
            drift_result.get("attribute_drifts")
        )
        html = tpl.render(
            drift=drift_result,
            attribute_drifts_rows=attr_rows,
            title=cfg.get("title"),
            status_class=_status_class(drift_result.get("overall_score")),
            raw_json=json.dumps(drift_result, indent=2, ensure_ascii=False, default=str),
        )
    else:
        tpl = env.get_template("eda_report.html")
        html = tpl.render(
            eda=eda_result or {},
            title=cfg.get("title"),
            raw_json=json.dumps(eda_result or {}, indent=2, ensure_ascii=False, default=str),
        )

    if fmt == "html":
        out_path.write_text(html, encoding="utf-8")
        return {
            "status": "success",
            "format": "html",
            "output_path": str(out_path),
            "size_bytes": out_path.stat().st_size,
            "renderer": "builtin",
        }

    if fmt == "pdf":
        from weasyprint import HTML
        HTML(string=html).write_pdf(str(out_path))
        return {
            "status": "success",
            "format": "pdf",
            "output_path": str(out_path),
            "size_bytes": out_path.stat().st_size,
            "renderer": "builtin",
        }

    raise typer.BadParameter(f"built-in fallback supports html|pdf|md; got {fmt!r}")


def _render_markdown(drift, eda, cfg) -> str:
    title = cfg.get("title") or ("Drift Report" if drift else "EDA Report")
    lines = [f"# {title}", ""]
    if drift is not None:
        lines.append(f"- modality: `{drift.get('modality', 'unknown')}`")
        lines.append(f"- timestamp: {drift.get('timestamp', 'n/a')}")
        lines.append(f"- overall_score: **{drift.get('overall_score', 0):.4f}**")
        if drift.get("status"):
            lines.append(f"- status: **{drift['status']}**")
        if drift.get("embedding_drift_detector"):
            lines.append(f"- embedding detector: `{drift['embedding_drift_detector']}`")
        normalized = _normalize_attribute_drifts(drift.get("attribute_drifts"))
        if normalized:
            lines += ["", "## Attribute drifts", ""]
            for name, score, extras in normalized:
                score_str = "—" if score is None else f"{score:.4f}"
                extras_str = (
                    " (" + ", ".join(f"{k}={v}" for k, v in extras.items()) + ")"
                    if extras else ""
                )
                lines.append(f"- `{name}`: {score_str}{extras_str}")
    if eda is not None:
        lines.append(f"- modality: `{eda.get('modality', 'unknown')}`")
        if "summary" in eda:
            lines += ["", "## Summary", ""]
            for k, v in eda["summary"].items():
                lines.append(f"- `{k}`: {v}")
    lines += ["", "## Raw envelope", "", "```json"]
    lines.append(json.dumps(drift if drift is not None else eda, indent=2, ensure_ascii=False, default=str))
    lines += ["```", ""]
    return "\n".join(lines)


report_app = typer.Typer(help="Render drift / EDA results to HTML / PDF / Markdown reports.")


@report_app.command("render")
def render_report(
    input: Path = typer.Option(
        ..., "--input", "-i",
        help="Path to a drift or EDA envelope JSON (e.g. the stdout of `ddoc analyze drift --json`).",
    ),
    output: Path = typer.Option(
        ..., "--out", "-o",
        help="Output report path. Format inferred from extension if --format omitted.",
    ),
    format: Optional[str] = typer.Option(
        None, "--format", "-f",
        help="Report format: html | pdf | md. Defaults to suffix of --out.",
    ),
    title: Optional[str] = typer.Option(
        None, "--title",
        help="Report title (defaults to 'Drift Report' / 'EDA Report').",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON envelope to stdout instead of pretty progress.",
    ),
):
    """Render a drift / EDA envelope to an HTML, PDF, or Markdown report.

    Examples:
        ddoc report render --input drift.json --out report.html
        ddoc report render -i drift.json -o report.pdf --title "Q4 release drift"
        ddoc report render -i eda.json -o eda.md
    """
    fmt = (format or output.suffix.lstrip(".")).lower()
    if fmt not in ("html", "pdf", "md"):
        rprint(f"[red]❌ Unsupported format: {fmt!r}. Pick one of: html, pdf, md.[/red]")
        raise typer.Exit(code=2)

    try:
        payload = _load_input(input)
    except typer.BadParameter as e:
        rprint(f"[red]❌ {e}[/red]")
        raise typer.Exit(code=2)
    except json.JSONDecodeError as e:
        rprint(f"[red]❌ Failed to parse {input}: {e}[/red]")
        raise typer.Exit(code=2)

    drift_result, eda_result = _classify_envelope(payload)
    cfg = {"title": title}

    # Try plugin hookimpls first; fall back to built-in if all return None.
    pm = get_pmgr().pm
    try:
        plugin_result = pm.hook.report_render(
            drift_result=drift_result,
            eda_result=eda_result,
            format=fmt,
            output_path=str(output),
            cfg=cfg,
        )
    except Exception as e:
        # Plugin failure shouldn't kill the CLI — fall through to fallback
        plugin_result = None
        if not json_out:
            rprint(f"[yellow]⚠️  plugin report_render raised: {e} — using built-in fallback[/yellow]")

    if plugin_result is not None:
        result = plugin_result
    else:
        try:
            result = _builtin_render(drift_result, eda_result, fmt, str(output), cfg)
        except Exception as e:
            msg = f"render failed: {e}"
            if json_out:
                sys.stdout.write(json.dumps({"status": "error", "error_code": "render_failed", "message": msg}) + "\n")
            else:
                rprint(f"[red]❌ {msg}[/red]")
            raise typer.Exit(code=1)

    if json_out:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    else:
        rprint(f"[green]✅ {result.get('format')} report → {result.get('output_path')} "
               f"({result.get('size_bytes', 0)} bytes, renderer={result.get('renderer', 'plugin')})[/green]")
