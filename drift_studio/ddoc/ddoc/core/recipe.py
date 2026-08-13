"""Multi-step recipe execution — Round 16.

A *recipe* is a YAML file describing an ordered sequence of ddoc CLI
invocations chained by file paths in/out. Each step's output (e.g.
the path of a freshly-generated drift envelope) can be referenced by
later steps via ``${steps.<id>.output}`` placeholders.

Schema (top level):

    name: optional human label
    description: optional
    vars: { key: value, ... }     # ${vars.key} substitutions
    steps:
      - id: string (unique per recipe)
        run: one of [fetch, analyze.eda, analyze.drift, examples.generate,
                     report.render, export.drift_report]
        with: { mapping of CLI option name → value }
        out: optional path used as this step's "output" reference

Reference syntax inside ``with`` values:

* ``${vars.<name>}`` — reads from the recipe's ``vars`` section
* ``${env.<NAME>}`` — reads from the process env
* ``${steps.<id>.output}`` — output path of a previous step
* ``${steps.<id>.json.<dotted.path>}`` — pulls a value from a previous
  step's JSON envelope (e.g. ``${steps.drift.json.overall_score}``)

The executor invokes the same hermetic ``ddoc`` subprocess each step
uses, captures the JSON envelope, and feeds it to the substitution
machinery. Failures stop the recipe; the error envelope is bubbled.

Why a recipe layer? Round 15 GUI / Round 14 REST cover one operation
at a time. Real workflows are usually `fetch → analyze → report →
export`. Recipes turn that 4-step dance into one invocation, and
shareable as a YAML file.
"""
from __future__ import annotations

import copy
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# Each step `run` token maps to (subcommand argv prefix, list of
# allowed `with` keys, special handling). Keeping this declarative
# means adding a new step type later is a one-line entry.
_STEP_KINDS: Dict[str, Dict[str, Any]] = {
    "fetch": {
        "argv": ["fetch"],
        "positional": ["source_uri"],
        "options": {
            "dest": "--dest",
            "symlink": "--symlink",         # bool flag
            "config": "--config",           # JSON-string serialized
        },
        "json_flag": True,
    },
    "examples.generate": {
        "argv": ["examples", "generate"],
        "positional": ["modality"],
        "options": {
            "out": "--out",
            "scenario": "--scenario",
        },
        "json_flag": False,                  # examples generate doesn't emit JSON envelope
    },
    "analyze.eda": {
        "argv": ["analyze", "eda"],
        "positional_optional": ["snapshot"],
        "options": {
            "data_path": "--data-path",
            "invalidate_cache": "--invalidate-cache",
            "save_snapshot": "--save-snapshot",
            "strict_hash": "--strict-hash",
            "quiet": "--quiet",
        },
        "json_flag": True,
    },
    "analyze.drift": {
        "argv": ["analyze", "drift"],
        "positional_optional": ["baseline", "current"],
        "options": {
            "data_path_ref": "--data-path-ref",
            "data_path_cur": "--data-path-cur",
            "detector": "--detector",
            "fusion": "--fusion",
            "fusion_weights": "--fusion-weights",
            "with_embeddings": "--with-embeddings",
            "quiet": "--quiet",
        },
        "json_flag": True,
    },
    "report.render": {
        "argv": ["report", "render"],
        "options": {
            "input": "-i",
            "out": "-o",
            "format": "--format",
            "title": "--title",
        },
        "json_flag": True,
    },
    "export.drift_report": {
        "argv": ["export", "drift-report"],
        "positional": ["input"],
        "options": {
            "target": "--to",
            "config": "--config",
        },
        "json_flag": True,
    },
    "train": {
        # R21 (alpr framework consolidation) — model training as a
        # recipe step. Dispatches to whatever plugin owns the named
        # ``trainer`` via the ``retrain_run`` hookspec.
        "argv": ["train"],
        "options": {
            "train_path": "--train-path",
            "trainer": "--trainer",
            "model_out": "--model-out",
            "params": "--params-json",  # dict → JSON string
        },
        "json_flag": True,
    },
    "transform": {
        # R49 (alpr PII/EDA plugin consolidation) — generic transform
        # step. Dispatches to whatever plugin owns the named
        # ``transform`` via the ``transform_apply`` hookspec
        # (ddoc-plugin-pii-eda → ``pii_blur``, etc.). Mirrors ``train``.
        "argv": ["transform"],
        "options": {
            "input_path": "--input-path",
            "transform": "--transform",
            "output_path": "--output-path",
            "args": "--args-json",  # dict → JSON string
        },
        "json_flag": True,
    },
}


# ── Errors ───────────────────────────────────────────────────────────


class RecipeError(Exception):
    """Recipe parse / execution failure."""

    def __init__(self, message: str, *, code: str = "recipe_error", step_id: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.step_id = step_id
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": "error",
            "error_code": self.code,
            "message": str(self),
            "step_id": self.step_id,
            **({"details": self.details} if self.details else {}),
        }


# ── Substitution ─────────────────────────────────────────────────────


import ast
import operator

_REF_PATTERN = re.compile(r"\$\{([^}]+)\}")


# ── ``when:`` mini-evaluator (Round 17) ──────────────────────────────


_ALLOWED_BINOPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
}
_ALLOWED_UNARYOPS = {
    ast.Not: operator.not_, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_when_node(node) -> Any:
    """Walk a parsed AST allowing only literals, comparisons, boolean
    ops, parentheses, and unary plus/minus/not. Anything else (Name,
    Call, Attribute, Subscript, etc.) → ValueError. The expression
    arrives with all ``${...}`` placeholders already resolved to JSON
    literals."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        op_fn = _ALLOWED_UNARYOPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"unsupported unary op {type(node.op).__name__}")
        return op_fn(_eval_when_node(node.operand))
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            r = True
            for v in node.values:
                r = _eval_when_node(v)
                if not r:
                    return r
            return r
        if isinstance(node.op, ast.Or):
            r = False
            for v in node.values:
                r = _eval_when_node(v)
                if r:
                    return r
            return r
        raise ValueError(f"unsupported boolop {type(node.op).__name__}")
    if isinstance(node, ast.Compare):
        left = _eval_when_node(node.left)
        for cmp_op, comp in zip(node.ops, node.comparators):
            op_fn = _ALLOWED_BINOPS.get(type(cmp_op))
            if op_fn is None:
                raise ValueError(f"unsupported compare op {type(cmp_op).__name__}")
            right = _eval_when_node(comp)
            if not op_fn(left, right):
                return False
            left = right
        return True
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


def _eval_when(expr: str, ctx: Dict[str, Any]) -> bool:
    """Evaluate a ``when:`` expression. Substitution first turns
    ``${steps.x.json.score}`` into ``0.42``; then we parse + walk a
    locked-down AST. Returns ``True`` to run the step, ``False`` to
    skip."""
    if expr is None:
        return True
    if isinstance(expr, bool):
        return expr
    expr_str = expr if isinstance(expr, str) else str(expr)
    expr_str = expr_str.strip()
    if not expr_str:
        return True
    # Substitute placeholders → JSON-literal text.
    def _to_literal(value: Any) -> str:
        if isinstance(value, str):
            return json.dumps(value)
        if value is None or isinstance(value, (bool, int, float)):
            return json.dumps(value)
        # Fallback: stringify; comparisons against non-scalar will likely
        # be a user error (raised below).
        return json.dumps(str(value))

    def _replace(match):
        return _to_literal(_resolve_ref(match.group(1).strip(), ctx))

    resolved = _REF_PATTERN.sub(_replace, expr_str)
    try:
        tree = ast.parse(resolved, mode="eval")
    except SyntaxError as e:
        raise RecipeError(
            f"`when` parse failed: {e.msg} — expr: {expr_str!r} (resolved: {resolved!r})",
            code="bad_when",
        ) from e
    try:
        result = _eval_when_node(tree.body)
    except ValueError as e:
        raise RecipeError(
            f"`when` evaluator: {e} — expr: {expr_str!r}",
            code="bad_when",
        ) from e
    return bool(result)


def _lookup_dotted(obj: Any, path: List[str]) -> Any:
    """``obj`` then index ``path`` step-by-step. Raises KeyError on miss."""
    cur = obj
    for p in path:
        if isinstance(cur, dict):
            if p not in cur:
                raise KeyError(p)
            cur = cur[p]
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError) as e:
                raise KeyError(p) from e
        else:
            raise KeyError(p)
    return cur


def _substitute(value: Any, ctx: Dict[str, Any]) -> Any:
    """Recursively walk ``value`` and resolve ``${...}`` placeholders.

    ``ctx`` shape: ``{vars: dict, env: dict, steps: {id: {output: str,
    json: dict}}}``.

    Whole-string references (``"${steps.x.json}"``) preserve the
    referenced object's type (so an envelope dict survives). Embedded
    references inside larger strings are stringified (``str(value)``).
    """
    if isinstance(value, dict):
        return {k: _substitute(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, ctx) for v in value]
    if not isinstance(value, str):
        return value

    matches = list(_REF_PATTERN.finditer(value))
    if not matches:
        return value

    # Whole-string single-ref shortcut: preserve type.
    if len(matches) == 1 and matches[0].group(0) == value:
        ref = matches[0].group(1).strip()
        return _resolve_ref(ref, ctx)

    out = []
    last = 0
    for m in matches:
        out.append(value[last:m.start()])
        ref = m.group(1).strip()
        resolved = _resolve_ref(ref, ctx)
        out.append("" if resolved is None else str(resolved))
        last = m.end()
    out.append(value[last:])
    return "".join(out)


def _resolve_ref(ref: str, ctx: Dict[str, Any]) -> Any:
    parts = ref.split(".")
    if not parts:
        raise RecipeError(f"empty placeholder: ${{{ref}}}", code="bad_placeholder")
    head, tail = parts[0], parts[1:]
    try:
        if head == "vars":
            return _lookup_dotted(ctx.get("vars", {}), tail)
        if head == "env":
            if len(tail) != 1:
                raise RecipeError(f"env reference must be ${{env.NAME}}: {ref}", code="bad_placeholder")
            return os.environ.get(tail[0], "")
        if head == "steps":
            if len(tail) < 2:
                raise RecipeError(
                    f"steps reference needs at least ${{steps.<id>.output|json[.path]}}: {ref}",
                    code="bad_placeholder",
                )
            step_id = tail[0]
            steps = ctx.get("steps", {})
            if step_id not in steps:
                raise RecipeError(
                    f"reference to unknown step: {step_id}", code="unknown_step_ref",
                    step_id=step_id,
                )
            kind = tail[1]
            if kind == "output":
                return steps[step_id].get("output")
            if kind == "json":
                env = steps[step_id].get("json")
                if env is None:
                    raise RecipeError(
                        f"step '{step_id}' did not produce a JSON envelope",
                        code="step_no_json", step_id=step_id,
                    )
                return _lookup_dotted(env, tail[2:]) if tail[2:] else env
            raise RecipeError(f"unsupported steps.* kind: {kind}", code="bad_placeholder")
        raise RecipeError(f"unknown placeholder root: {head}", code="bad_placeholder")
    except KeyError as e:
        raise RecipeError(f"placeholder ${{{ref}}} could not be resolved (missing key {e!s})",
                          code="bad_placeholder")


# ── Build argv from a step ───────────────────────────────────────────


@dataclass
class StepResult:
    id: str
    run: str
    argv: List[str]
    returncode: int
    elapsed_ms: int
    output: Optional[str] = None
    json: Optional[Dict[str, Any]] = None
    skipped: bool = False
    skipped_reason: Optional[str] = None  # "when" | "dry_run"


def _step_to_argv(run_kind: str, with_args: Dict[str, Any]) -> List[str]:
    spec = _STEP_KINDS.get(run_kind)
    if spec is None:
        raise RecipeError(f"unknown step kind: {run_kind}", code="unknown_step_kind")
    args: List[str] = list(spec["argv"])
    consumed: set = set()
    # positionals (required)
    for name in spec.get("positional", []):
        if name not in with_args:
            raise RecipeError(f"step {run_kind} requires `with.{name}`", code="missing_with")
        args.append(str(with_args[name]))
        consumed.add(name)
    # positionals (optional, in declared order; only emit if present)
    for name in spec.get("positional_optional", []):
        if name in with_args and with_args[name] not in (None, ""):
            args.append(str(with_args[name]))
        consumed.add(name)
    # options
    options = spec.get("options", {})
    for key, flag in options.items():
        if key not in with_args:
            continue
        consumed.add(key)
        v = with_args[key]
        if v is None or v is False or v == "":
            continue
        if v is True:
            args.append(flag)
            continue
        if isinstance(v, (dict, list)):
            v = json.dumps(v, default=str)
        args += [flag, str(v)]
    leftovers = set(with_args) - consumed
    if leftovers:
        raise RecipeError(
            f"step {run_kind}: unknown `with` keys: {sorted(leftovers)}",
            code="unknown_with_key",
        )
    if spec.get("json_flag"):
        args.append("--json")
    return args


# ── Loading + validation ─────────────────────────────────────────────


@dataclass
class Recipe:
    name: Optional[str]
    description: Optional[str]
    vars: Dict[str, Any]
    steps: List[Dict[str, Any]]
    workspace: Optional[str] = None
    source_path: Optional[Path] = None
    # R22 — list of plugin entry-point names the recipe needs (e.g.
    # `["ddoc_vision", "ddoc_alpr"]`). Empty list = no requirement
    # (back-compat default).
    required_plugins: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "Recipe":
        p = Path(path)
        if not p.exists():
            raise RecipeError(f"recipe not found: {p}", code="recipe_not_found")
        try:
            import yaml
        except ImportError:
            raise RecipeError(
                "recipes need PyYAML (already in core deps; reinstall ddoc).",
                code="yaml_missing",
            )
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise RecipeError(f"YAML parse failed: {e}", code="bad_yaml")
        if not isinstance(data, dict):
            raise RecipeError("recipe top-level must be a mapping", code="bad_recipe")
        steps = data.get("steps") or []
        if not isinstance(steps, list) or not steps:
            raise RecipeError("recipe must have at least one step", code="bad_recipe")
        # R22 — top-level ``required_plugins:`` field. Validation is
        # done lazily (against the actual entry-points) inside
        # ``check_plugin_requirements`` so loading stays cheap.
        req = data.get("required_plugins") or []
        if not isinstance(req, list) or not all(isinstance(x, str) for x in req):
            raise RecipeError(
                "`required_plugins` must be a list of strings",
                code="bad_required_plugins",
            )
        return cls(
            name=data.get("name"),
            description=data.get("description"),
            vars=dict(data.get("vars") or {}),
            steps=copy.deepcopy(steps),
            workspace=data.get("workspace"),
            source_path=p,
            required_plugins=list(req),
        )

    def check_plugin_requirements(
        self, installed: Optional[List[str]] = None,
    ) -> List[str]:
        """Return the subset of ``self.required_plugins`` that aren't
        currently installed. Empty list = all satisfied.

        ``installed`` lets callers inject a known plugin list (useful
        for testing). When None, scans setuptools entry-points in the
        ``ddoc`` group via ``importlib.metadata``.
        """
        if not self.required_plugins:
            return []
        if installed is None:
            try:
                import importlib.metadata as _md
                eps = _md.entry_points(group="ddoc")
                installed = [ep.name for ep in eps]
            except Exception:
                installed = []
        installed_set = set(installed)
        return [p for p in self.required_plugins if p not in installed_set]

    def validate(self) -> List[str]:
        """Return a list of human-readable issues; empty list = OK."""
        issues: List[str] = []
        seen_ids: set = set()
        for i, step in enumerate(self.steps):
            label = f"step #{i + 1}"
            if not isinstance(step, dict):
                issues.append(f"{label}: must be a mapping")
                continue
            # Round 18 — parallel block: each child must validate too.
            if "parallel" in step:
                children = step.get("parallel") or []
                if not isinstance(children, list) or not children:
                    issues.append(f"{label}: `parallel:` must list at least one nested step")
                    continue
                for j, child in enumerate(children):
                    clabel = f"{label}.parallel[{j}]"
                    if not isinstance(child, dict):
                        issues.append(f"{clabel}: must be a mapping")
                        continue
                    issues.extend(self._validate_single_step(child, clabel, seen_ids))
                continue
            issues.extend(self._validate_single_step(step, label, seen_ids))
        return issues

    @staticmethod
    def _validate_single_step(step: Dict[str, Any], label: str, seen_ids: set) -> List[str]:
        out: List[str] = []
        sid = step.get("id")
        if not sid:
            out.append(f"{label}: missing `id`")
        elif sid in seen_ids:
            out.append(f"{label}: duplicate id {sid!r}")
        else:
            seen_ids.add(sid)
        run = step.get("run")
        if run not in _STEP_KINDS:
            out.append(f"{label} {sid or '?'}: unknown `run` {run!r}; supported: {sorted(_STEP_KINDS)}")
        with_args = step.get("with") or {}
        if not isinstance(with_args, dict):
            out.append(f"{label} {sid or '?'}: `with` must be a mapping")
        return out


# ── Execution ───────────────────────────────────────────────────────


def execute_recipe(
    recipe: Recipe,
    *,
    dry_run: bool = False,
    on_step: Optional[callable] = None,
) -> Dict[str, Any]:
    """Run all steps in order. Returns ``{status, recipe, steps:
    [StepResult-as-dict]}``.

    ``on_step`` is invoked with each ``StepResult`` after it
    completes (live progress callback).
    """
    issues = recipe.validate()
    if issues:
        raise RecipeError(
            "recipe failed validation",
            code="validation_failed",
            details={"issues": issues},
        )

    # R22 — check required_plugins BEFORE any step runs so the
    # operator gets a focused install-this-plugin error rather than a
    # mid-pipeline failure with traceback.
    missing = recipe.check_plugin_requirements()
    if missing:
        raise RecipeError(
            f"recipe requires plugins not installed: {sorted(missing)}",
            code="missing_required_plugins",
            details={
                "missing": sorted(missing),
                "hint": (
                    "Install with: "
                    + " && ".join(f"pip install {p.replace('_', '-')}"
                                    for p in sorted(missing))
                ),
            },
        )

    # Late-import the runner so unit tests that just want to validate
    # recipes don't need uvicorn / fastapi pulled in.
    from ddoc.server import runner  # type: ignore[no-untyped-call]

    # Resolve workspace dir for auto envelope persistence. Each
    # JSON-emitting step writes its envelope to
    # ``<workspace>/<step_id>.envelope.json`` so subsequent steps can
    # reference the file via ``${steps.<id>.output}`` when no explicit
    # ``out`` path is provided.
    workspace = _resolve_workspace(recipe)

    ctx: Dict[str, Any] = {"vars": dict(recipe.vars), "env": {}, "steps": {}}
    out_steps: List[Dict[str, Any]] = []

    for raw_step in recipe.steps:
        # Round 18 — ``parallel:`` block. The block's children are run
        # via a ThreadPoolExecutor; each sees the same ctx-snapshot
        # taken just before the block (so siblings cannot reference
        # each other, only earlier serial steps). After the group
        # completes, all child step IDs are merged into ctx so the
        # next serial step can reference any of them.
        if isinstance(raw_step, dict) and "parallel" in raw_step:
            children = raw_step["parallel"] or []
            if not isinstance(children, list) or not children:
                raise RecipeError(
                    "`parallel:` must list at least one nested step",
                    code="bad_parallel",
                )
            results, fail_envelope = _run_parallel_group(
                children, ctx, dry_run, runner, workspace, on_step,
            )
            for sr in results:
                # Re-merge into ctx in declaration order to keep
                # downstream reference resolution deterministic.
                ctx["steps"][sr.id] = {"output": sr.output, "json": sr.json}
                out_steps.append(_stepresult_to_dict(sr))
            if fail_envelope is not None:
                _record_recipe_metrics(out_steps, success=False)
                return {
                    "status": "error",
                    "recipe": recipe.name,
                    "failed_step": fail_envelope["failed_step"],
                    "error": fail_envelope["error"],
                    "steps": out_steps,
                }
            continue

        sr, error_envelope = _run_single_step(
            raw_step, ctx, dry_run, runner, workspace,
        )
        ctx["steps"][sr.id] = {
            "output": sr.output if not error_envelope else None,
            "json": sr.json,
        }
        out_steps.append(_stepresult_to_dict(sr))
        if on_step:
            on_step(sr)
        if error_envelope is not None:
            _record_recipe_metrics(out_steps, success=False)
            return {
                "status": "error",
                "recipe": recipe.name,
                "failed_step": sr.id,
                "error": error_envelope,
                "steps": out_steps,
            }

    _record_recipe_metrics(out_steps, success=True)
    return {
        "status": "success",
        "recipe": recipe.name,
        "steps": out_steps,
    }


def _record_recipe_metrics(out_steps, *, success: bool) -> None:
    """Best-effort metrics emission — safe to call when ddoc.server
    isn't imported (CLI-only invocations)."""
    try:
        from ddoc.server.metrics import record_recipe_run, record_recipe_step
    except Exception:
        return
    try:
        record_recipe_run(success=success)
        for s in out_steps:
            if s.get("skipped"):
                reason = s.get("skipped_reason") or "unknown"
                record_recipe_step(s.get("run", "?"), f"skipped_{reason}")
            elif s.get("returncode", 0) == 0:
                record_recipe_step(s.get("run", "?"), "ok")
            else:
                record_recipe_step(s.get("run", "?"), "error")
    except Exception:
        pass


def _run_single_step(raw_step, ctx, dry_run, runner, workspace):
    """Execute one regular (non-parallel-block) recipe step.

    Returns ``(StepResult, error_envelope_or_None)``. Substitution and
    ``when:`` evaluation happen here so the parallel-block path can
    reuse the same logic via a thread pool.
    """
    sid = raw_step["id"]
    run_kind = raw_step["run"]
    with_args = _substitute(raw_step.get("with") or {}, ctx)
    out_path = _substitute(raw_step.get("out"), ctx) if raw_step.get("out") else None

    argv = _step_to_argv(run_kind, with_args)
    sr = StepResult(id=sid, run=run_kind, argv=argv, returncode=0, elapsed_ms=0)

    when_expr = raw_step.get("when")
    if when_expr is not None and not _eval_when(when_expr, ctx):
        sr.skipped = True
        sr.skipped_reason = "when"
        return sr, None

    if dry_run:
        sr.skipped = True
        sr.skipped_reason = "dry_run"
        sr.output = out_path
        return sr, None

    spec = _STEP_KINDS[run_kind]
    require_json = bool(spec.get("json_flag"))
    t0 = time.monotonic()
    try:
        res = runner.run(argv, require_json=require_json)
        sr.returncode = res.returncode
        sr.elapsed_ms = res.elapsed_ms
        sr.json = res.json or None
        sr.output = out_path or _infer_output(run_kind, with_args, res.json)
        if require_json and sr.json is not None and sr.output is None:
            env_path = workspace / f"{sid}.envelope.json"
            _atomic_json_write(env_path, sr.json)
            sr.output = str(env_path)
        return sr, None
    except runner.RunError as e:
        sr.returncode = e.returncode if e.returncode is not None else -1
        sr.elapsed_ms = int((time.monotonic() - t0) * 1000)
        sr.json = e.json_partial
        return sr, e.to_dict()


def _run_parallel_group(children, ctx, dry_run, runner, workspace, on_step):
    """Run all ``children`` concurrently. Returns ``(results_in_decl_order,
    fail_envelope_or_None)``. Fail envelope carries the first failing
    child's ``RunError.to_dict()``; remaining children still complete
    so their results are visible (parallel execution doesn't cancel
    siblings — easier to debug)."""
    from concurrent.futures import ThreadPoolExecutor
    if not children:
        return [], None

    # Snapshot ctx so concurrent threads each see the same view.
    snapshot = {
        "vars": dict(ctx.get("vars", {})),
        "env": dict(ctx.get("env", {})),
        "steps": dict(ctx.get("steps", {})),
    }

    def _job(idx_and_step):
        idx, raw = idx_and_step
        sr, err = _run_single_step(raw, snapshot, dry_run, runner, workspace)
        return idx, sr, err

    indexed = list(enumerate(children))
    results: List = [None] * len(children)
    failures: List = []
    with ThreadPoolExecutor(max_workers=len(children)) as pool:
        for idx, sr, err in pool.map(_job, indexed):
            results[idx] = sr
            if on_step:
                on_step(sr)
            if err is not None:
                failures.append((sr.id, err))

    if failures:
        first_id, first_err = failures[0]
        return results, {"failed_step": first_id, "error": first_err}
    return results, None


def _infer_output(run_kind: str, with_args: Dict[str, Any], envelope: Optional[Dict[str, Any]]) -> Optional[str]:
    """Best-effort guess for ``step.output`` when not explicitly set.

    Convention: steps that write a file expose its path. ``examples
    generate`` / ``fetch`` use the explicit ``--out`` / ``--dest``;
    ``report render`` uses ``-o``; ``export drift-report`` uses the
    envelope's ``output_path`` field; analyze steps return the
    in-memory envelope only (callers reference ``${steps.<id>.json}``).
    """
    if run_kind == "report.render":
        return with_args.get("out")
    if run_kind == "fetch":
        if envelope and isinstance(envelope, dict):
            return envelope.get("local_path") or with_args.get("dest")
        return with_args.get("dest")
    if run_kind == "examples.generate":
        return with_args.get("out")
    if run_kind == "export.drift_report":
        return (envelope or {}).get("output_path")
    return None


def _resolve_workspace(recipe: Recipe) -> Path:
    """Resolve the recipe's auto-envelope workspace dir. Honors the
    top-level ``workspace:`` field if set; otherwise creates a
    deterministic per-recipe-source path under ``<source_dir>/.ddoc-recipe-out``,
    or falls back to a unique tmp dir for inline recipes."""
    if recipe.workspace:
        d = Path(recipe.workspace)
    elif recipe.source_path:
        d = recipe.source_path.parent / ".ddoc-recipe-out" / recipe.source_path.stem
    else:
        import tempfile
        d = Path(tempfile.mkdtemp(prefix="ddoc-recipe-"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _atomic_json_write(path: Path, payload: Dict[str, Any]) -> None:
    """Write JSON atomically — temp file then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)


def _stepresult_to_dict(sr: StepResult) -> Dict[str, Any]:
    return {
        "id": sr.id,
        "run": sr.run,
        "argv": sr.argv,
        "returncode": sr.returncode,
        "elapsed_ms": sr.elapsed_ms,
        "output": sr.output,
        "json": sr.json,
        "skipped": sr.skipped,
        "skipped_reason": sr.skipped_reason,
    }
