"""``/examples`` — modality × scenario discovery + generator."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..auth import require_api_key
from ..app import map_envelope_to_response
from ..runner import run
from ..schemas import ExamplesGenerateRequest

router = APIRouter(tags=["examples"], dependencies=[Depends(require_api_key)])


@router.get("/examples/scenarios")
def scenarios() -> Dict[str, Any]:
    """Return the modality × scenario matrix the factories module
    advertises. Mirror of ``ddoc examples list``."""
    try:
        from ddoc.cli.commands.examples import _import_factories
        factories = _import_factories()
    except Exception as e:
        return {"status": "error", "error_code": "factories_unavailable", "message": str(e)}
    return {
        "status": "ok",
        "modalities": list(factories.PAIR_BUILDERS.keys()),
        "scenarios": list(factories.SUPPORTED_SCENARIOS),
    }


@router.post("/examples/generate")
def examples_generate(req: ExamplesGenerateRequest):
    """``ddoc examples generate <modality> --out <out> --scenario <s>``.

    Note: ``ddoc examples generate`` doesn't currently emit a JSON
    envelope on stdout (Track A shipped pretty-only output). For the
    REST facade we bypass JSON parsing — the runner returns ``None``
    json on success but stdout/stderr are captured for diagnostics.
    """
    args = [
        "examples", "generate", req.modality,
        "--out", req.out,
        "--scenario", req.scenario,
    ]
    result = run(args, require_json=False, timeout=120.0)
    return {
        "status": "ok",
        "modality": req.modality,
        "out": req.out,
        "scenario": req.scenario,
        "ref_dir": f"{req.out}/ref",
        "cur_dir": f"{req.out}/cur",
        "elapsed_ms": result.elapsed_ms,
    }
