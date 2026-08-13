"""``/analyze/{eda,drift,drift/stream}`` — wraps ddoc analyze."""
from __future__ import annotations

import json
import queue
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..app import map_envelope_to_response
from ..auth import require_api_key
from ..runner import RunError, run, run_streamed
from ..schemas import AnalyzeDriftRequest, AnalyzeEdaRequest

router = APIRouter(tags=["analyze"], dependencies=[Depends(require_api_key)])


# ── Build argv lists from request models ─────────────────────────────


def _eda_argv(req: AnalyzeEdaRequest) -> List[str]:
    args: List[str] = ["analyze", "eda"]
    if req.snapshot:
        args.append(req.snapshot)
    if req.data_path:
        args += ["--data-path", req.data_path]
    if req.invalidate_cache:
        args.append("--invalidate-cache")
    if req.save_snapshot:
        args.append("--save-snapshot")
    if req.strict_hash:
        args.append("--strict-hash")
    args.append("--json")
    if req.quiet:
        args.append("--quiet")
    return args


def _drift_argv(req: AnalyzeDriftRequest, *, include_progress_flag: bool = False) -> List[str]:
    args: List[str] = ["analyze", "drift"]
    if req.baseline:
        args.append(req.baseline)
    if req.current:
        args.append(req.current)
    if req.data_path_ref:
        args += ["--data-path-ref", req.data_path_ref]
    if req.data_path_cur:
        args += ["--data-path-cur", req.data_path_cur]
    if req.detector and req.detector != "default":
        args += ["--detector", req.detector]
    if req.with_embeddings:
        args.append("--with-embeddings")
    if req.fusion and req.fusion != "none":
        args += ["--fusion", req.fusion]
    if req.fusion_weights:
        args += ["--fusion-weights", req.fusion_weights]
    args.append("--json")
    if req.quiet:
        args.append("--quiet")
    if include_progress_flag:
        args.append("--ndjson-progress")
    return args


# ── R-D4: inline cfg → tempdir path-mode adapter ────────────────────


@contextmanager
def _materialize_cfg(cfg: Dict[str, Any]) -> Iterator[Tuple[str, str]]:
    """Write inline cfg dicts into temp ``distributions[_series].json``
    files under a scratch dir and yield ``(ref_dir, cur_dir)`` paths
    suitable for CLI path-mode (`--data-path-ref/cur`).

    Supported cfg shapes:
      - dict-of-counts: ``baseline_categorical / current_categorical``
        (R26-A `ddoc-plugin-categorical`)
      - series-of-dists: ``baseline_categorical_series / current_categorical_series``
        (R33 `ddoc-plugin-keti-temporal`)
    """
    base_cat = cfg.get("baseline_categorical")
    cur_cat = cfg.get("current_categorical")
    base_ser = cfg.get("baseline_categorical_series")
    cur_ser = cfg.get("current_categorical_series")
    with tempfile.TemporaryDirectory(prefix="ddoc-rest-cfg-") as tmp:
        ref_dir = Path(tmp) / "ref"
        cur_dir = Path(tmp) / "cur"
        ref_dir.mkdir()
        cur_dir.mkdir()
        if base_cat is not None or cur_cat is not None:
            (ref_dir / "distributions.json").write_text(
                json.dumps(base_cat or {}), encoding="utf-8",
            )
            (cur_dir / "distributions.json").write_text(
                json.dumps(cur_cat or {}), encoding="utf-8",
            )
        if base_ser is not None or cur_ser is not None:
            (ref_dir / "distributions_series.json").write_text(
                json.dumps({"series": base_ser or []}), encoding="utf-8",
            )
            (cur_dir / "distributions_series.json").write_text(
                json.dumps({"series": cur_ser or []}), encoding="utf-8",
            )
        yield str(ref_dir), str(cur_dir)


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/analyze/eda")
def analyze_eda(req: AnalyzeEdaRequest):
    """Wrap ``ddoc analyze eda --json``."""
    args = _eda_argv(req)
    result = run(args, require_json=True, timeout=req.timeout_sec)
    return map_envelope_to_response(result.json)


@router.post("/analyze/drift")
def analyze_drift(req: AnalyzeDriftRequest):
    """Wrap ``ddoc analyze drift --json``.

    R-D4: when ``req.cfg`` is set, the server materializes the inline
    cfg into temp dist files and invokes path-mode internally. This
    lets cross-container HTTP callers (keti) send dict-of-counts /
    series without a shared volume.
    """
    if req.cfg:
        with _materialize_cfg(req.cfg) as (ref_dir, cur_dir):
            req2 = req.model_copy(update={
                "data_path_ref": ref_dir,
                "data_path_cur": cur_dir,
                "cfg": None,  # avoid recursion into materialize
            })
            args = _drift_argv(req2)
            result = run(args, require_json=True, timeout=req.timeout_sec)
        return map_envelope_to_response(result.json)
    args = _drift_argv(req)
    result = run(args, require_json=True, timeout=req.timeout_sec)
    return map_envelope_to_response(result.json)


@router.post("/analyze/drift/stream")
def analyze_drift_stream(req: AnalyzeDriftRequest):
    """Server-Sent Events stream of NDJSON progress + final envelope.

    Event types:

    * ``progress`` — `{"progress": 0..1, "stage": "...", "message": "..."}`
    * ``result`` — final ddoc envelope (success or in-band error)
    * ``error`` — RunError envelope (subprocess failure)

    Clients consume via ``EventSource`` (browser) or
    ``curl -N --header 'Accept: text/event-stream'``.
    """
    args = _drift_argv(req, include_progress_flag=True)
    q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
    SENTINEL: Dict[str, Any] = {"__done__": True}

    def _on_progress(obj: Dict[str, Any]) -> None:
        q.put({"event": "progress", "data": obj})

    def _runner():
        try:
            res = run_streamed(args, on_progress=_on_progress, timeout=req.timeout_sec)
            q.put({"event": "result", "data": res.json})
        except RunError as err:
            q.put({"event": "error", "data": err.to_dict()})
        except Exception as err:  # noqa: BLE001
            q.put({
                "event": "error",
                "data": {
                    "status": "error",
                    "error_type": "exception",
                    "message": str(err),
                },
            })
        finally:
            q.put(SENTINEL)

    threading.Thread(target=_runner, name="ddoc-serve-drift-stream", daemon=True).start()

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
