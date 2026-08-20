"""Reference-engine ladder demo (Round 37).

Standalone, additive proof-of-life for ddoc-plugin-reference-engine
(Round 34) -- the plugin has its own pytest suite and was CLI-smoke-
tested manually, but until this router nothing in drift_studio
backend/frontend ever invoked --detector reference_engine, and there
was no UI showing its output.

Deliberately does NOT touch app/routers/drift.py (Dataset-ORM-coupled,
--detector hardcoded to DDOC_DRIFT_DETECTOR) or its DB-backed pathway.
This router has no database dependency at all -- fixed demo, no request
body, no persistence beyond what the ddoc subprocess itself writes.

Reuses app.services.ddoc_runner.run_ddoc -- the same subprocess
primitive drift.py's _run_drift_via_cli uses -- against a committed,
deterministic toy fixture (see
backend/scripts/generate_reference_engine_demo_fixture.py for how it
was generated; the fixture itself is committed, not regenerated
per-request).
"""
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.services.ddoc_runner import DdocError, run_ddoc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reference-engine", tags=["reference-engine-demo"])

# ddoc_plugin_reference_engine.reference_engine_impl.MODALITY -- duplicated
# here (not imported) since the backend doesn't depend on the plugin
# package directly, only invokes it as a subprocess via run_ddoc.
MODALITY = "timeseries_reference"

# backend/app/routers/reference_engine_demo.py -> backend/app/ -> sample_data/...
_FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "sample_data" / "reference_engine_demo"
_REF_PATH = _FIXTURE_ROOT / "ref"
_CUR_PATH = _FIXTURE_ROOT / "cur"

# ddoc-plugin-reference-engine's own EventStore defaults its persistence
# root to Path.cwd() of whatever process calls it. Pointing the
# subprocess's cwd here -- rather than letting it inherit the backend
# process's own cwd (e.g. /app in the container) -- keeps each demo
# run's auto-detected-candidate-event side effect (.ddoc/events/*.yaml)
# in one predictable, OS-managed scratch location instead of scattering
# it into the app's actual working directory.
_RUNTIME_SCRATCH = Path(tempfile.gettempdir()) / "ddoc_reference_engine_demo"


@router.post("/demo")
def run_reference_engine_demo():
    """Run the level0-4 ladder against the committed toy fixture and
    return the plugin's JSON envelope as-is. No parameters -- fixed
    demo, nothing to configure."""
    if not _REF_PATH.is_dir() or not _CUR_PATH.is_dir():
        raise HTTPException(
            status_code=500,
            detail=(
                f"reference-engine demo fixture not found at {_FIXTURE_ROOT} "
                "(expected ref/toy_metrics/ and cur/toy_metrics/ subdirectories -- "
                "run backend/scripts/generate_reference_engine_demo_fixture.py)"
            ),
        )
    _RUNTIME_SCRATCH.mkdir(parents=True, exist_ok=True)

    args = [
        "analyze", "drift",
        "--data-path-ref", str(_REF_PATH),
        "--data-path-cur", str(_CUR_PATH),
        "--detector", "reference_engine",
        "--json",
    ]
    try:
        out = run_ddoc(args, cwd=str(_RUNTIME_SCRATCH), timeout=60)
    except DdocError as e:
        logger.warning("[reference-engine-demo] ddoc subprocess failed: %s", e.to_dict())
        raise HTTPException(
            status_code=500,
            detail={"error": "ddoc subprocess failed", "ddoc": e.to_dict()},
        )

    return _unwrap_single_modality(out.json)


def _unwrap_single_modality(payload: dict) -> dict:
    """The CLI's multi-plugin merge always nests results under
    modalities.<name>, even when (as here, since --detector pins exactly
    one plugin) only one modality could ever respond. Flatten that one
    entry back to the top level so callers see the plugin's own envelope
    directly, instead of leaking the general multi-plugin merge shape
    into a demo endpoint that structurally can never have more than one."""
    modalities = payload.get("modalities")
    if isinstance(modalities, dict) and MODALITY in modalities:
        return modalities[MODALITY]
    return payload
