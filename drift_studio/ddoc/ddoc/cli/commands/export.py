"""``ddoc export drift-report`` — ship a drift result to an external system.

Round 11 (Track C) — first concrete user of the new
``export_drift_report`` hookspec. The CLI:

1. Reads the drift envelope JSON from disk.
2. Tries the hookspec — if any plugin returns a non-None result, use that.
3. Falls back to built-in adapters: ``keti_veritas`` (HTTP POST to
   ``<base_url>/field-agents/drift-report``) and ``file`` (atomic JSON
   write into ``<out_dir>/drift_<utc_ts>.json``).

The on-the-wire schema mirrors ``keti_veritas/app/services/dia/
dd_export_hook.py`` (DriftReport, protocol 1.0) so the receiving side
doesn't need to know the report originated from ddoc rather than from
keti_veritas's own export hook.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich import print as rprint

from .utils import get_pmgr


# ── Helpers ───────────────────────────────────────────────────────────


def _load_envelope(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise typer.BadParameter(f"input file does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_target_config(config_file: Optional[Path], inline_config: Optional[str]) -> Dict[str, Any]:
    """Read target_config from either ``--config-file <yaml>`` or
    ``--config <json>``. Both are optional (some adapters work with
    env-only)."""
    cfg: Dict[str, Any] = {}
    if config_file:
        if not config_file.exists():
            raise typer.BadParameter(f"config file does not exist: {config_file}")
        text = config_file.read_text(encoding="utf-8").strip()
        if config_file.suffix in (".yaml", ".yml"):
            try:
                import yaml
                cfg.update(yaml.safe_load(text) or {})
            except ImportError:
                raise typer.BadParameter("yaml support requires `pip install pyyaml`")
        else:
            cfg.update(json.loads(text))
    if inline_config:
        cfg.update(json.loads(inline_config))
    return cfg


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, data: str) -> None:
    """Write data atomically — temp file then rename. Avoids leaving
    a half-written report behind if the process is killed mid-write."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


def _build_drift_report_envelope(
    drift_result: Dict[str, Any],
    target_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Wrap a ddoc drift_result in the keti_veritas DriftReport schema
    (protocol 1.0). Mirror of the structure produced by
    ``keti_veritas/app/services/dia/dd_export_hook.py`` so the
    receiving end is symmetric whether ddoc or keti_veritas built it.
    """
    source = target_config.get("source") or {
        "app_id": target_config.get("app_id", "ddoc-cli"),
        "app_type": "drift_analysis",
    }
    overall = drift_result.get("overall_score", 0)
    if overall is None:
        overall = 0
    severity = drift_result.get("status")
    if not severity:
        severity = (
            "critical" if overall >= 0.25
            else "warning" if overall >= 0.15
            else "normal"
        )

    return {
        "protocol_version": "1.0",
        "source": source,
        "drift": {
            "snapshot_id": drift_result.get("snapshot_id"),
            "model_name": target_config.get("model_name"),
            "modality": drift_result.get("modality"),
            "scores": {
                "overall": float(overall),
                "attribute": drift_result.get("attribute_drift_overall"),
                "embedding": drift_result.get("embedding_drift"),
            },
            "severity": severity,
            "embedding_drift_detector": drift_result.get("embedding_drift_detector"),
        },
        "diagnosis": {
            "recommendations": target_config.get("recommendations", []),
        },
        "fingerprint": drift_result.get("fingerprint", {}),
        "raw": drift_result,
        "sent_at": _utc_iso(),
    }


# ── Built-in adapters ─────────────────────────────────────────────────


def _adapter_file(envelope: Dict[str, Any], target_config: Dict[str, Any]) -> Dict[str, Any]:
    out_dir = Path(target_config.get("out_dir") or ".")
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = target_config.get("filename")
    if not filename:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        modality = envelope.get("drift", {}).get("modality") or "drift"
        filename = f"drift_{ts}_{modality}.json"
    out_path = out_dir / filename
    _atomic_write(out_path, json.dumps(envelope, indent=2, ensure_ascii=False, default=str))
    return {
        "status": "success",
        "target": "file",
        "transmitted_at": envelope["sent_at"],
        "output_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
    }


def _adapter_keti_veritas(envelope: Dict[str, Any], target_config: Dict[str, Any]) -> Dict[str, Any]:
    base_url = target_config.get("base_url")
    if not base_url:
        raise typer.BadParameter("keti_veritas adapter requires `base_url` in target_config")
    timeout = float(target_config.get("timeout_sec", 30))
    api_key = target_config.get("api_key")

    url = base_url.rstrip("/") + target_config.get("path", "/field-agents/drift-report")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        import httpx  # ddoc backend already pulls httpx via fastapi tests
        # httpx logs each request at INFO via stdlib logging; some CLI
        # invocations have a global root handler that goes to stdout,
        # which would corrupt the --json envelope. Pin to WARNING for
        # the duration of this call.
        import logging
        _httpx_log = logging.getLogger("httpx")
        _saved_level = _httpx_log.level
        _httpx_log.setLevel(logging.WARNING)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=envelope, headers=headers)
        finally:
            _httpx_log.setLevel(_saved_level)
        return {
            "status": "success" if response.is_success else "error",
            "target": "keti_veritas",
            "transmitted_at": envelope["sent_at"],
            "url": url,
            "http_status": response.status_code,
            "response_body_preview": response.text[:500],
        }
    except ImportError:
        # Fall back to stdlib urllib if httpx unavailable.
        import urllib.request
        import urllib.error
        body = json.dumps(envelope, default=str).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                preview = resp.read(500).decode("utf-8", errors="replace")
                return {
                    "status": "success",
                    "target": "keti_veritas",
                    "transmitted_at": envelope["sent_at"],
                    "url": url,
                    "http_status": resp.status,
                    "response_body_preview": preview,
                }
        except urllib.error.HTTPError as e:
            return {
                "status": "error",
                "target": "keti_veritas",
                "transmitted_at": envelope["sent_at"],
                "url": url,
                "http_status": e.code,
                "response_body_preview": e.read(500).decode("utf-8", errors="replace"),
            }


_BUILTIN_ADAPTERS = {
    "file": _adapter_file,
    "keti_veritas": _adapter_keti_veritas,
}


# ── CLI ───────────────────────────────────────────────────────────────


export_app = typer.Typer(help="Export drift / EDA results to external systems (file / HTTP / etc.).")


@export_app.command("drift-report")
def export_drift_report(
    input: Path = typer.Argument(
        ..., help="Drift envelope JSON (stdout of `ddoc analyze drift --json`).",
    ),
    target: str = typer.Option(
        ..., "--to", "-t",
        help="Destination adapter. Built-in: keti_veritas | file. Plugins can register more.",
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config-file",
        help="YAML / JSON file with target-specific options. keti_veritas: {base_url, api_key?, timeout_sec?, source}. file: {out_dir, filename?}.",
    ),
    config: Optional[str] = typer.Option(
        None, "--config",
        help="Inline JSON object for target_config (alternative to --config-file).",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit the result envelope as a single JSON object on stdout.",
    ),
):
    """Ship a drift result to an external system.

    Examples:
        ddoc export drift-report drift.json --to file --config '{"out_dir":"/tmp/exports"}'
        ddoc export drift-report drift.json --to keti_veritas \\
            --config '{"base_url":"http://veritas.local:8000","api_key":"..."}'
    """
    try:
        drift_result = _load_envelope(input)
    except typer.BadParameter as e:
        rprint(f"[red]❌ {e}[/red]")
        raise typer.Exit(code=2)
    except json.JSONDecodeError as e:
        rprint(f"[red]❌ Failed to parse {input}: {e}[/red]")
        raise typer.Exit(code=2)

    try:
        target_config = _load_target_config(config_file, config)
    except typer.BadParameter as e:
        rprint(f"[red]❌ {e}[/red]")
        raise typer.Exit(code=2)

    # 1. Try plugin hookimpls.
    pm = get_pmgr().pm
    try:
        plugin_result = pm.hook.export_drift_report(
            drift_result=drift_result,
            target=target,
            target_config=target_config,
        )
    except Exception as e:
        plugin_result = None
        if not json_out:
            rprint(f"[yellow]⚠️  plugin export_drift_report raised: {e} — falling back to built-in[/yellow]")

    if plugin_result is not None:
        result = plugin_result
    else:
        # 2. Built-in fallback.
        adapter = _BUILTIN_ADAPTERS.get(target)
        if adapter is None:
            err = {
                "status": "error",
                "error_code": "unsupported_target",
                "target": target,
                "message": (
                    f"no plugin handled target={target!r} and built-in adapters cover only "
                    f"{sorted(_BUILTIN_ADAPTERS.keys())}."
                ),
            }
            if json_out:
                sys.stdout.write(json.dumps(err, ensure_ascii=False) + "\n")
            else:
                rprint(f"[red]❌ {err['message']}[/red]")
            raise typer.Exit(code=2)

        envelope = _build_drift_report_envelope(drift_result, target_config)
        try:
            result = adapter(envelope, target_config)
        except typer.BadParameter as e:
            rprint(f"[red]❌ {e}[/red]")
            raise typer.Exit(code=2)
        except Exception as e:
            err = {
                "status": "error",
                "error_code": "adapter_failed",
                "target": target,
                "message": f"{type(e).__name__}: {e}",
            }
            if json_out:
                sys.stdout.write(json.dumps(err, ensure_ascii=False) + "\n")
            else:
                rprint(f"[red]❌ {err['message']}[/red]")
            raise typer.Exit(code=1)

    if json_out:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    else:
        rprint(f"[green]✅ exported to {target} — {result.get('status')}[/green]")
        if "output_path" in result:
            rprint(f"   path: {result['output_path']}")
        if "url" in result:
            rprint(f"   url: {result['url']} (http {result.get('http_status')})")
