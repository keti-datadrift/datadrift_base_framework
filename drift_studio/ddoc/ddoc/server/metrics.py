"""Prometheus metrics for ``ddoc serve`` (Round 19).

Uses ``prometheus_client`` if installed; falls back to a pure-Python
zero-deps text-format generator so the endpoint is always available
without an extra install. The pure-Python path is deliberately small —
just counter / histogram-summary in the simplest text format.

Exposed metrics:

* ``ddoc_http_requests_total{path, method, status}`` — counter
* ``ddoc_http_request_duration_seconds{path}`` — histogram (buckets
  fixed at 0.05/0.1/0.25/0.5/1/2.5/5/10/30/60s)
* ``ddoc_recipe_runs_total{result}`` — counter (result ∈
  {success, error})
* ``ddoc_recipe_steps_total{kind, status}`` — counter (status ∈
  {ok, error, skipped_when, skipped_dry})
* ``ddoc_runner_calls_total{result}`` — counter (subprocess wrapper)
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, Tuple


# Histogram bucket boundaries (seconds) — same shape as
# prometheus_client's default for HTTP latency.
_HIST_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)


class _MetricsRegistry:
    """Tiny thread-safe in-process registry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # counter name → labels-tuple (sorted (k,v)) → value
        self._counters: Dict[str, Dict[Tuple, float]] = defaultdict(lambda: defaultdict(float))
        # histogram name → labels-tuple → {buckets: list[count], sum, count}
        self._histograms: Dict[str, Dict[Tuple, Dict]] = defaultdict(lambda: defaultdict(self._empty_hist))

    @staticmethod
    def _empty_hist() -> Dict:
        return {"buckets": [0] * len(_HIST_BUCKETS), "sum": 0.0, "count": 0}

    @staticmethod
    def _label_key(labels: Dict[str, str]) -> Tuple:
        return tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            self._counters[name][self._label_key(labels)] += value

    def observe(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            entry = self._histograms[name][self._label_key(labels)]
            for i, ub in enumerate(_HIST_BUCKETS):
                if value <= ub:
                    entry["buckets"][i] += 1
            entry["sum"] += value
            entry["count"] += 1

    def render(self) -> str:
        """Return Prometheus text exposition format."""
        out: list[str] = []
        with self._lock:
            counters = {n: dict(v) for n, v in self._counters.items()}
            hists = {n: {k: dict(v) for k, v in d.items()} for n, d in self._histograms.items()}

        for name, by_labels in sorted(counters.items()):
            out.append(f"# HELP {name} ddoc serve counter")
            out.append(f"# TYPE {name} counter")
            for lk, val in by_labels.items():
                lbl = _format_labels(lk)
                out.append(f"{name}{lbl} {val}")
        for name, by_labels in sorted(hists.items()):
            out.append(f"# HELP {name} ddoc serve histogram")
            out.append(f"# TYPE {name} histogram")
            for lk, h in by_labels.items():
                lbl_parts = list(lk)
                lbl_parts.append(("le", "+Inf"))
                # cumulative bucket counts
                cum = 0
                for i, ub in enumerate(_HIST_BUCKETS):
                    cum += h["buckets"][i]
                    parts = list(lk) + [("le", _fmt_bucket(ub))]
                    out.append(f"{name}_bucket{_format_labels(parts)} {cum}")
                out.append(f"{name}_bucket{_format_labels(lbl_parts)} {h['count']}")
                out.append(f"{name}_sum{_format_labels(lk)} {h['sum']}")
                out.append(f"{name}_count{_format_labels(lk)} {h['count']}")
        return "\n".join(out) + "\n"


def _format_labels(labels) -> str:
    if not labels:
        return ""
    parts = ",".join(f'{k}="{_escape(str(v))}"' for k, v in labels)
    return "{" + parts + "}"


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _fmt_bucket(b: float) -> str:
    if b == int(b):
        return str(int(b))
    return f"{b:g}"


# Module-level singleton. Tests / app share it.
REGISTRY = _MetricsRegistry()


# ── Public helpers ──────────────────────────────────────────────────


def record_http(path: str, method: str, status: int, duration_sec: float) -> None:
    REGISTRY.inc("ddoc_http_requests_total", path=path, method=method, status=str(status))
    REGISTRY.observe("ddoc_http_request_duration_seconds", duration_sec, path=path)


def record_recipe_run(success: bool) -> None:
    REGISTRY.inc("ddoc_recipe_runs_total", result="success" if success else "error")


def record_recipe_step(kind: str, status: str) -> None:
    REGISTRY.inc("ddoc_recipe_steps_total", kind=kind, status=status)


def record_runner_call(success: bool) -> None:
    REGISTRY.inc("ddoc_runner_calls_total", result="success" if success else "error")


# ── HTTP middleware factory ─────────────────────────────────────────


def install_middleware(app) -> None:
    """Wire request-level metrics. Strips dynamic path segments so the
    counter cardinality stays bounded (e.g. ``/recipes/{name}`` →
    ``/recipes/:name``)."""
    @app.middleware("http")
    async def _metrics_middleware(request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        try:
            template = _route_template(request)
            record_http(template, request.method, response.status_code,
                        time.monotonic() - start)
        except Exception:  # noqa: BLE001
            pass
        return response


def _route_template(request) -> str:
    """Best-effort path template — collapses ``/recipes/abc`` → ``/recipes/:name``
    so we don't leak unbounded labels into the registry."""
    path = request.url.path
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return path
