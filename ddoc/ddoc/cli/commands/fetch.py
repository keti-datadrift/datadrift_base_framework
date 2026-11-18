"""``ddoc fetch`` — materialize a remote data source into a local dir.

Round 13 — first concrete user of the ``data_source_read`` hookspec.
Built-in fallback handles ``file://`` (and bare paths) by copying or
sym-linking the source dir; plugins can register additional schemes
(``s3://``, ``gs://``, ``http(s)://``, ``kafka://``) via the same
hook so an operator can run::

    ddoc fetch s3://bucket/datasets/ref --dest /tmp/ref
    ddoc analyze drift --data-path-ref /tmp/ref --data-path-cur ...

without ddoc itself needing to know about S3.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import typer
from rich import print as rprint

from .utils import get_pmgr


def _builtin_file_read(source_uri: str, dest_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Built-in adapter for ``file://`` URIs and bare paths.

    Copies the source into ``<dest_dir>/<basename>`` (or creates a
    symlink when ``config.symlink == True``). Returns the same envelope
    shape plugins should produce.
    """
    parsed = urlparse(source_uri)
    if parsed.scheme in ("", "file"):
        src = Path(parsed.path or source_uri)
    else:
        raise typer.BadParameter(
            f"built-in adapter only handles file:// or bare paths, got {source_uri!r}"
        )
    if not src.exists():
        raise typer.BadParameter(f"source does not exist: {src}")

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / src.name

    use_symlink = bool(config.get("symlink", False))
    bytes_transferred = 0
    files_count = 0

    if use_symlink:
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(src.resolve())
        # Symlink doesn't transfer bytes; just count the resolved tree.
        for p in src.rglob("*") if src.is_dir() else [src]:
            if p.is_file():
                files_count += 1
                bytes_transferred += p.stat().st_size
    else:
        if src.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(src, target)
            for p in target.rglob("*"):
                if p.is_file():
                    files_count += 1
                    bytes_transferred += p.stat().st_size
        else:
            shutil.copy2(src, target)
            files_count = 1
            bytes_transferred = target.stat().st_size

    return {
        "status": "success",
        "scheme": "file",
        "source_uri": source_uri,
        "local_path": str(target),
        "bytes_transferred": bytes_transferred,
        "files_count": files_count,
        "adapter": "builtin",
    }


def fetch_command(
    source_uri: str = typer.Argument(
        ..., help="Source URI (file:///path, s3://bucket/key, gs://..., http(s)://..., or a bare path).",
    ),
    dest: Path = typer.Option(
        ..., "--dest", "-d",
        help="Local directory to materialize into (created if missing).",
    ),
    symlink: bool = typer.Option(
        False, "--symlink",
        help="For file:// sources, create a symlink instead of copying (faster, but no isolation).",
    ),
    config: Optional[str] = typer.Option(
        None, "--config",
        help="Adapter-specific JSON config (e.g. '{\"region\":\"us-east-1\"}' for s3 plugins).",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit a single-line JSON envelope instead of pretty progress.",
    ),
):
    """Pull data from ``source_uri`` into ``dest`` so subsequent
    ``ddoc analyze`` calls can use it as a path-mode input.

    Examples:
        ddoc fetch /data/ref --dest /tmp/work
        ddoc fetch file:///mnt/share/audit --dest /tmp/audit --symlink
        ddoc fetch s3://my-bucket/datasets/ref --dest /tmp/ref --config '{"region":"us-west-2"}'
    """
    cfg: Dict[str, Any] = {"symlink": symlink}
    if config:
        try:
            cfg.update(json.loads(config))
        except json.JSONDecodeError as e:
            rprint(f"[red]❌ --config must be valid JSON: {e}[/red]")
            raise typer.Exit(code=2)

    # 1. Try plugins first (firstresult=True; first claim wins).
    pm = get_pmgr().pm
    try:
        plugin_result = pm.hook.data_source_read(
            source_uri=source_uri, dest_dir=str(dest), config=cfg,
        )
    except Exception as e:
        plugin_result = None
        if not json_out:
            rprint(f"[yellow]⚠️  data_source_read plugin raised: {e} — falling back to built-in[/yellow]")

    if plugin_result is not None:
        result = plugin_result
    else:
        # 2. Built-in fallback (file:// only).
        try:
            result = _builtin_file_read(source_uri, str(dest), cfg)
        except typer.BadParameter as e:
            err = {
                "status": "error",
                "error_code": "no_adapter_for_scheme",
                "source_uri": source_uri,
                "message": (
                    f"{e} — install a plugin that handles this scheme, "
                    "or pass a file:// URI / bare path."
                ),
            }
            if json_out:
                sys.stdout.write(json.dumps(err, ensure_ascii=False) + "\n")
            else:
                rprint(f"[red]❌ {err['message']}[/red]")
            raise typer.Exit(code=2)
        except Exception as e:
            err = {"status": "error", "error_code": "fetch_failed", "message": str(e)}
            if json_out:
                sys.stdout.write(json.dumps(err, ensure_ascii=False) + "\n")
            else:
                rprint(f"[red]❌ {err['message']}[/red]")
            raise typer.Exit(code=1)

    if json_out:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    else:
        rprint(f"[green]✅ {result.get('scheme')} → {result.get('local_path')}[/green]")
        rprint(f"   files: {result.get('files_count')}  bytes: {result.get('bytes_transferred')}  "
               f"adapter: {result.get('adapter', 'plugin')}")
