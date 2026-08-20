"""Reference-engine ladder demo router (Round 37). No DB dependency --
mounts just this router on a throwaway FastAPI() instance rather than
importing app.main, which pulls in every other router's (heavier) deps
at module load time (sqlalchemy/torch/etc -- the same friction hit
during Round 36's manual HTTP smoke test). Mock target is
app.routers.reference_engine_demo.run_ddoc (the name copied into this
module's namespace via `from ... import run_ddoc`), not
app.services.ddoc_runner.run_ddoc -- patching the source module is a
no-op against that copied reference.
"""
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import reference_engine_demo
from app.services.ddoc_runner import DdocError, DdocResult

app = FastAPI()
app.include_router(reference_engine_demo.router)
client = TestClient(app)


def _fake_success_result():
    return DdocResult(
        argv=["python", "-m", "ddoc.cli.main", "analyze", "drift"],
        returncode=0, stdout="{}", stderr_tail="", elapsed_ms=42,
        json={
            "status": "success", "backend": "reference-engine", "detector": "reference_engine",
            "overall_score": 0.5,
            "attribute_drifts": {"toy_metrics/revenue": 1.0, "toy_metrics/visits": 0.0},
            "results": {
                "toy_metrics/revenue": {
                    "evaluation_window": {"start": "2025-12-02", "end": "2025-12-31"},
                    "levels": {"L0_고정기준선": {"status": "alert", "z_score": 12.3,
                                                "expected": 6500.0, "actual": 9800.0,
                                                "reason": "...", "attribution_confidence": None}},
                },
                "toy_metrics/visits": {
                    "evaluation_window": {"start": "2025-12-02", "end": "2025-12-31"},
                    "levels": {"L0_고정기준선": {"status": "quiet", "z_score": 0.4,
                                                "expected": 4980.0, "actual": 5010.0,
                                                "reason": "...", "attribution_confidence": None}},
                },
            },
            "new_candidate_events": [], "pending_candidate_events": [],
        },
    )


def test_demo_passes_through_run_ddoc_json_on_success():
    with patch.object(reference_engine_demo, "run_ddoc", return_value=_fake_success_result()) as mock_run:
        resp = client.post("/reference-engine/demo")

    assert resp.status_code == 200
    body = resp.json()
    assert body["results"]["toy_metrics/revenue"]["levels"]["L0_고정기준선"]["status"] == "alert"
    assert body["results"]["toy_metrics/visits"]["levels"]["L0_고정기준선"]["status"] == "quiet"

    called_args = mock_run.call_args.args[0]
    assert called_args[called_args.index("--detector") + 1] == "reference_engine"
    assert "--data-path-ref" in called_args and "--data-path-cur" in called_args


def test_demo_returns_500_with_ddoc_error_detail_on_subprocess_failure():
    err = DdocError(
        "ddoc subprocess exited 1", error_type="nonzero_exit",
        returncode=1, stderr_tail="boom", elapsed_ms=10,
        argv=["python", "-m", "ddoc.cli.main"],
    )
    with patch.object(reference_engine_demo, "run_ddoc", side_effect=err):
        resp = client.post("/reference-engine/demo")

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["ddoc"]["error_type"] == "nonzero_exit"
    assert detail["ddoc"]["stderr_tail"] == "boom"


def test_demo_500s_with_clear_message_when_fixture_directory_missing():
    with patch.object(reference_engine_demo, "_REF_PATH") as fake_ref:
        fake_ref.is_dir.return_value = False
        resp = client.post("/reference-engine/demo")

    assert resp.status_code == 500
    assert "fixture" in resp.json()["detail"].lower()
