"""``GET /commands`` — CLI introspection for GUI auto-population.

Returns the structure of ``ddoc --help`` (and every subcommand)
parsed into a machine-readable shape. The Round-15 GUI consumes this
to render form builders without hardcoding option lists. Mirrors the
``fleet help-json`` pattern from the gpu-tunnel reference (Round 14
plan §1).
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from ..auth import require_api_key

router = APIRouter(tags=["commands"], dependencies=[Depends(require_api_key)])


def _click_param_dict(p) -> Dict[str, Any]:
    """Serialize a click.Parameter / Option / Argument into JSON."""
    info: Dict[str, Any] = {
        "name": p.name,
        "type": _type_name(p),
        "required": getattr(p, "required", False),
        "is_flag": getattr(p, "is_flag", False),
        "default": _safe_default(p),
        "help": getattr(p, "help", None),
    }
    if getattr(p, "opts", None):
        info["opts"] = list(p.opts)
    if getattr(p, "secondary_opts", None):
        info["secondary_opts"] = list(p.secondary_opts)
    return info


def _type_name(p) -> str:
    t = getattr(p, "type", None)
    if t is None:
        return "string"
    name = type(t).__name__
    # click types: STRING, INT, FLOAT, BOOL, Path, Choice
    if name == "Choice":
        choices = list(getattr(t, "choices", []))
        return f"choice[{','.join(choices)}]"
    if name == "Path":
        return "path"
    return getattr(t, "name", name).lower()


def _safe_default(p) -> Any:
    d = getattr(p, "default", None)
    # click stores callable defaults as functions; resolve to None for serialization.
    if callable(d):
        return None
    try:
        # Reject anything not JSON-serializable.
        import json
        json.dumps(d)
        return d
    except (TypeError, ValueError):
        return None


def _walk_command(cmd, name: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "name": name,
        "help": getattr(cmd, "help", None) or getattr(cmd, "short_help", None),
        "params": [],
        "subcommands": {},
    }
    for p in getattr(cmd, "params", []) or []:
        try:
            info["params"].append(_click_param_dict(p))
        except Exception:
            continue
    # Typer / click groups expose `commands` dict.
    sub = getattr(cmd, "commands", None) or {}
    for sub_name, sub_cmd in sub.items():
        try:
            info["subcommands"][sub_name] = _walk_command(sub_cmd, sub_name)
        except Exception:
            continue
    return info


@router.get("/commands")
def commands() -> Dict[str, Any]:
    """Return the full ddoc CLI command tree as JSON."""
    from ddoc.cli.main import app as _ddoc_app
    import typer

    # Typer's `app.click_object` is the click Group built lazily.
    # We need a click context to build it properly.
    click_app = typer.main.get_command(_ddoc_app)
    return {
        "name": click_app.name or "ddoc",
        "tree": _walk_command(click_app, click_app.name or "ddoc"),
    }
