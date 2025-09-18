from __future__ import annotations
import json
import typer
from typing import Optional, Dict, Any
from rich import print
from dd.core.plugins import get_plugin_manager
from dd.core.pipeline import PipelineRunner

pm = get_plugin_manager().pm

app = typer.Typer(help="dd subcommands")

@app.command()
def eda(input: str, modality: str = "table", out: str = "report.json"):
    """Run EDA via plugins."""
    results = pm.hook.eda_run(input_path=input, modality=modality, output_path=out)
    print(_pretty(results))

@app.command()
def transform(input: str, transform: str, args: Optional[str] = None, out: str = "out.txt"):
    """Apply a transform via plugins."""
    _args = json.loads(args) if args else {}
    results = pm.hook.transform_apply(input_path=input, transform=transform, args=_args, output_path=out)
    print(_pretty(results))

@app.command()
def drift(ref: str, cur: str, detector: str = "ks", cfg: Optional[str] = None, out: str = "drift.json"):
    """Detect drift via plugins."""
    _cfg = json.loads(cfg) if cfg else None
    results = pm.hook.drift_detect(ref_path=ref, cur_path=cur, detector=detector, cfg=_cfg, output_path=out)
    print(_pretty(results))

@app.command()
def reconstruct(input: str, method: str = "drop-empty", args: Optional[str] = None, out: str = "recon.txt"):
    """Reconstruct data via plugins."""
    _args = json.loads(args) if args else {}
    results = pm.hook.reconstruct_apply(input_path=input, method=method, args=_args, output_path=out)
    print(_pretty(results))

@app.command()
def retrain(train: str, trainer: str = "sklearn", params: Optional[str] = None, model_out: str = "model.json"):
    """Retrain a model via plugins."""
    _params = json.loads(params) if params else {}
    results = pm.hook.retrain_run(train_path=train, trainer=trainer, params=_params, model_out=model_out)
    print(_pretty(results))

@app.command()
def monitor(source: str, mode: str = "offline", schedule: Optional[str] = None):
    """Run monitors via plugins."""
    results = pm.hook.monitor_run(source=source, mode=mode, schedule=schedule)
    print(_pretty(results))

@app.command("pipeline-run")
def pipeline_run(steps_json: str):
    """Run a simple linear pipeline from a JSON string.

    Example:
      dd pipeline-run '{"steps":[
        {"type":"eda","input":"in.txt","modality":"table","out":"eda.json"},
        {"type":"drift","ref":"in.txt","cur":"in2.txt","detector":"toy","out":"drift.json"}
      ]}'
    """
    data = json.loads(steps_json)
    steps = data.get("steps", [])
    runner = PipelineRunner()
    results = runner.run(steps)
    print(results)

def _pretty(results: Any) -> str:
    # pluggy returns a list of results (one per plugin)
    try:
        return json.dumps(results, indent=2, ensure_ascii=False)
    except Exception:
        return str(results)