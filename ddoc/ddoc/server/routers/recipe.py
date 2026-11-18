"""``/recipe/{validate,run,run/stream}`` — Round 17.

Wraps the Round-16 recipe layer over HTTP. Supports both inline YAML
text (``body.yaml``) and on-disk paths (``body.path``); inline is the
ergonomic mode for the GUI's recipe builder, path mode mirrors the
``ddoc recipe run <path>`` CLI invocation for scripted callers that
already version their recipes alongside the project.

The streaming variant uses the same SSE event shape as
``/analyze/drift/stream``: ``event: progress`` per step, ``event:
result`` for the final envelope, ``event: error`` on failure.
"""
from __future__ import annotations

import json
import queue
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from ..auth import require_api_key
from ..schemas import RecipeBody

router = APIRouter(tags=["recipe"], dependencies=[Depends(require_api_key)])


# ── Helpers ─────────────────────────────────────────────────────────


def _load_recipe(body: RecipeBody):
    """Materialize a ``RecipeBody`` into a ``Recipe`` instance.

    Inline YAML is written to a tempfile so the executor's workspace
    auto-allocation has a stable anchor (uses the recipe's
    ``source_path`` to derive ``.ddoc-recipe-out/<stem>/``).
    """
    from ddoc.core.recipe import Recipe, RecipeError

    if not body.yaml and not body.path:
        return None, _bad("Recipe body needs `yaml` or `path`.", code="missing_recipe_input")
    if body.yaml and body.path:
        return None, _bad("Recipe body must not set both `yaml` and `path`.", code="conflicting_recipe_input")

    if body.path:
        try:
            return Recipe.load(body.path), None
        except RecipeError as e:
            return None, _bad(str(e), code=e.code, status=400)

    # Inline YAML.
    tmp = Path(tempfile.mkstemp(prefix="ddoc-recipe-", suffix=".yaml")[1])
    tmp.write_text(body.yaml, encoding="utf-8")
    try:
        return Recipe.load(tmp), None
    except RecipeError as e:
        return None, _bad(str(e), code=e.code, status=400)


def _bad(message: str, *, code: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"status": "error", "error_code": code, "message": message},
    )


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/recipe/validate")
def validate_recipe(body: RecipeBody):
    """Parse + structurally validate a recipe without running anything."""
    recipe, err = _load_recipe(body)
    if err is not None:
        return err
    issues = recipe.validate()
    return {
        "status": "ok" if not issues else "error",
        "recipe": recipe.name,
        "step_count": len(recipe.steps),
        "issues": issues,
    }


@router.post("/recipe/run")
def run_recipe(body: RecipeBody):
    """Execute the recipe synchronously."""
    from ddoc.core.recipe import RecipeError, execute_recipe

    recipe, err = _load_recipe(body)
    if err is not None:
        return err
    try:
        result = execute_recipe(recipe, dry_run=body.dry_run)
    except RecipeError as e:
        return JSONResponse(status_code=400, content=e.to_dict())
    status = 200 if result.get("status") == "success" else 500
    return JSONResponse(status_code=status, content=result)


@router.post("/recipe/run/stream")
def run_recipe_stream(body: RecipeBody):
    """SSE: ``event: progress`` per step, ``event: result`` at the end."""
    from ddoc.core.recipe import RecipeError, execute_recipe

    recipe, err = _load_recipe(body)
    if err is not None:
        return err

    q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
    SENTINEL: Dict[str, Any] = {"__done__": True}

    def _on_step(sr) -> None:
        q.put({"event": "progress", "data": {
            "id": sr.id,
            "run": sr.run,
            "argv": sr.argv,
            "returncode": sr.returncode,
            "elapsed_ms": sr.elapsed_ms,
            "output": sr.output,
            "skipped": sr.skipped,
            "json_summary": _envelope_summary(sr.json),
        }})

    def _runner():
        try:
            result = execute_recipe(recipe, dry_run=body.dry_run, on_step=_on_step)
            q.put({"event": "result", "data": result})
        except RecipeError as e:
            q.put({"event": "error", "data": e.to_dict()})
        except Exception as e:  # noqa: BLE001
            q.put({
                "event": "error",
                "data": {"status": "error", "error_type": "exception", "message": str(e)},
            })
        finally:
            q.put(SENTINEL)

    threading.Thread(target=_runner, name="ddoc-serve-recipe-stream", daemon=True).start()

    def _gen():
        while True:
            item = q.get()
            if item is SENTINEL or item.get("__done__"):
                break
            event = item.get("event", "message")
            data = item.get("data", {})
            yield f"event: {event}\ndata: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _envelope_summary(env):
    """Trim a step's envelope to a small dict for the progress event.

    Full envelope can be huge (vision plugin's per-image attribute
    cache) — sending it on every step would bloat the SSE stream.
    Clients that need the full payload read it from the final
    ``result`` event's ``steps[*].json``.
    """
    if not isinstance(env, dict):
        return None
    keep = {}
    for k in ("status", "modality", "overall_score", "fused_score", "format",
              "output_path", "size_bytes", "target", "files_count",
              "scheme", "transmitted_at", "error_code", "error_type"):
        if k in env:
            keep[k] = env[k]
    return keep
