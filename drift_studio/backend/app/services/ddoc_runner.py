"""subprocess wrapper for invoking the ddoc CLI from the backend.

Phase 3 of the orchestrator pivot — see
``/Users/jpark/.claude/plans/modular-wandering-tiger.md`` and
``_specs/architecture_consolidation.md`` Round-2.

The backend used to import ddoc as a Python library
(``from ddoc.core.workspace import ...``) and reimplement drift / eda
as separate services (``app.services.drift_service``, ``eda_service``)
— a "duplicate implementation" the spec already flagged. The pivot
keeps the HTTP API shape stable but routes the analytical work through
``ddoc analyze drift|eda --json`` invocations. This module is the
single entry point for that subprocess plumbing:

* ``run_ddoc(args)`` — synchronous, blocks the caller, returns
  ``DdocResult``.
* ``DdocResult.json`` — parsed stdout JSON (machine-readable contract
  established by ``--json`` in ``ddoc analyze drift|eda``).
* ``DdocError`` — raised when the subprocess fails or stdout doesn't
  look like JSON.

Process invocation form is intentionally hermetic
(``[sys.executable, "-m", "ddoc.cli.main", ...]``) rather than relying
on ``ddoc`` being on PATH inside the container. Errors include the
last ~4 KiB of stderr so the FastAPI 500 response can surface a
helpful message without leaking the full plugin traceback.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


DEFAULT_TIMEOUT_SEC = int(os.getenv("DDOC_RUNNER_DEFAULT_TIMEOUT_SEC", "600"))
STDERR_TAIL_BYTES = 4096


# ── Phase 6 — invocation counter (orchestrator pivot rollout telemetry) ──
#
# Tracks how often the subprocess (ddoc CLI) path is hit vs the legacy
# in-process path. Surfaced via /healthz so operators can decide when to
# flip BACKEND_USE_DDOC_CLI default to true (and eventually delete the
# legacy services). In-memory; resets on process restart.
_INVOCATIONS: dict[str, int] = {
    "ddoc_cli_calls": 0,
    "ddoc_cli_errors": 0,
    "ddoc_cli_total_elapsed_ms": 0,
    "legacy_calls_drift": 0,
    "legacy_calls_eda": 0,
}


def increment_counter(key: str, delta: int = 1) -> None:
    """Bump an invocation counter (no-op for unknown keys)."""
    if key in _INVOCATIONS:
        _INVOCATIONS[key] = _INVOCATIONS[key] + delta


def get_counters() -> dict[str, int]:
    """Snapshot of invocation counters for /healthz."""
    return dict(_INVOCATIONS)


# ── Errors ────────────────────────────────────────────────────────────


class DdocError(Exception):
    """Wraps a failed ``ddoc`` subprocess invocation.

    ``error_type`` is one of: ``timeout`` | ``nonzero_exit`` |
    ``invalid_json`` | ``empty_stdout``. ``stderr_tail`` is the trailing
    ~4 KiB of stderr captured during the run (or empty for ``timeout``).
    """

    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        returncode: Optional[int] = None,
        stderr_tail: str = "",
        elapsed_ms: Optional[int] = None,
        argv: Optional[list[str]] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.returncode = returncode
        self.stderr_tail = stderr_tail
        self.elapsed_ms = elapsed_ms
        self.argv = argv or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": str(self),
            "returncode": self.returncode,
            "stderr_tail": self.stderr_tail,
            "elapsed_ms": self.elapsed_ms,
            "argv": self.argv,
        }


# ── Result ────────────────────────────────────────────────────────────


@dataclass
class DdocResult:
    """Successful ``ddoc`` invocation outcome.

    ``stdout`` carries the raw ``--json`` envelope; ``json`` is the
    parsed dict (parsed lazily — empty dict on parse failure with
    ``json_parse_error`` populated). Callers should prefer ``json``.
    """

    argv: list[str]
    returncode: int
    stdout: str
    stderr_tail: str
    elapsed_ms: int
    json: dict[str, Any] = field(default_factory=dict)
    json_parse_error: Optional[str] = None


# ── Public entry ──────────────────────────────────────────────────────


def run_ddoc(
    args: list[str],
    *,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    env_extra: Optional[dict[str, str]] = None,
    require_json: bool = True,
) -> DdocResult:
    """Invoke ``python -m ddoc.cli.main <args>`` synchronously.

    Args:
        args: CLI arguments *after* ``ddoc``. Example:
            ``["analyze", "drift", "--data-path-ref", "/a",
              "--data-path-cur", "/b", "--json"]``
        cwd: working directory for the subprocess. Defaults to current
            process cwd.
        timeout: max seconds. Defaults to ``DDOC_RUNNER_DEFAULT_TIMEOUT_SEC``
            env (default 600). Pass ``0`` for no timeout (not recommended
            in request-handler context).
        env_extra: additional env vars to inject (merged on top of the
            inherited environment). Useful for ``DDOC_*`` knobs without
            polluting the parent process.
        require_json: when True (default), the subprocess must emit at
            least one parseable JSON object on stdout — otherwise a
            ``DdocError`` is raised with ``error_type="invalid_json"``
            or ``"empty_stdout"``. When False, raw stdout is returned
            and ``DdocResult.json`` may be empty.

    Returns:
        ``DdocResult`` on success.

    Raises:
        ``DdocError`` on timeout, non-zero exit, or invalid stdout.
    """
    timeout_eff: Optional[float] = (
        None if (timeout is not None and timeout <= 0)
        else (timeout if timeout is not None else DEFAULT_TIMEOUT_SEC)
    )

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    # Hermetic invocation — bind to this Python interpreter and the
    # installed ddoc package, regardless of PATH. Avoids "ddoc not found"
    # in containers where /usr/local/bin isn't on the worker process's
    # PATH.
    argv = [sys.executable, "-m", "ddoc.cli.main", *args]

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_eff,
            text=True,
        )
    except subprocess.TimeoutExpired as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        increment_counter("ddoc_cli_errors")
        raise DdocError(
            f"ddoc subprocess timed out after {timeout_eff}s",
            error_type="timeout",
            stderr_tail=_tail((e.stderr or "")[-STDERR_TAIL_BYTES:] if isinstance(e.stderr, str) else ""),
            elapsed_ms=elapsed_ms,
            argv=argv,
        ) from e

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    stderr_tail = _tail(proc.stderr or "")
    increment_counter("ddoc_cli_calls")
    increment_counter("ddoc_cli_total_elapsed_ms", elapsed_ms)

    if proc.returncode != 0:
        increment_counter("ddoc_cli_errors")
        raise DdocError(
            f"ddoc subprocess exited {proc.returncode}",
            error_type="nonzero_exit",
            returncode=proc.returncode,
            stderr_tail=stderr_tail,
            elapsed_ms=elapsed_ms,
            argv=argv,
        )

    stdout = proc.stdout or ""
    parsed: dict[str, Any] = {}
    parse_err: Optional[str] = None
    if require_json:
        if not stdout.strip():
            raise DdocError(
                "ddoc subprocess produced no stdout (expected --json envelope)",
                error_type="empty_stdout",
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
                elapsed_ms=elapsed_ms,
                argv=argv,
            )
        # The CLI emits one JSON object per invocation; some commands may
        # additionally print rich-mode noise. Pick the *last* parseable
        # JSON object in stdout (common convention).
        parsed_obj = _try_parse_last_json_object(stdout)
        if parsed_obj is None:
            raise DdocError(
                "ddoc subprocess stdout was not valid JSON",
                error_type="invalid_json",
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
                elapsed_ms=elapsed_ms,
                argv=argv,
            )
        parsed = parsed_obj
    else:
        parsed_obj = _try_parse_last_json_object(stdout)
        if parsed_obj is not None:
            parsed = parsed_obj
        else:
            parse_err = "stdout was not parseable as JSON (require_json=False)"

    return DdocResult(
        argv=argv,
        returncode=proc.returncode,
        stdout=stdout,
        stderr_tail=stderr_tail,
        elapsed_ms=elapsed_ms,
        json=parsed,
        json_parse_error=parse_err,
    )


# ── Streaming variant (Phase 6 — NDJSON progress) ─────────────────────


ProgressCallback = Callable[[dict[str, Any]], None]


def run_ddoc_streamed(
    args: list[str],
    *,
    on_progress: Optional[ProgressCallback] = None,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    env_extra: Optional[dict[str, str]] = None,
    require_json: bool = True,
    stderr_buffer_lines: int = 2048,
) -> DdocResult:
    """Streaming variant of ``run_ddoc`` for long-running analyses.

    Spawns the same hermetic ``python -m ddoc.cli.main`` invocation but
    consumes stderr line-by-line in a background thread. Lines that
    successfully parse as JSON objects with a ``progress`` field are
    forwarded to ``on_progress``; everything else is buffered for the
    error tail. Stdout is collected whole and parsed identically to
    ``run_ddoc`` once the process exits.

    The caller is expected to enable progress emission by passing
    ``--ndjson-progress`` inside ``args`` — without that flag the ddoc
    CLI emits nothing on stderr and the callback never fires (silent
    fallback to the plain run shape).

    ``on_progress`` callbacks run on the reader thread; keep them small
    (e.g. push to ``progress_tracker`` or update a Celery task state)
    and treat exceptions as recoverable — they are caught and logged
    via stderr buffer rather than killing the subprocess.
    """
    timeout_eff: Optional[float] = (
        None if (timeout is not None and timeout <= 0)
        else (timeout if timeout is not None else DEFAULT_TIMEOUT_SEC)
    )

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    argv = [sys.executable, "-m", "ddoc.cli.main", *args]

    stderr_buf: deque[str] = deque(maxlen=stderr_buffer_lines)

    def _consume_stderr(stream) -> None:
        try:
            for raw in stream:
                line = raw.rstrip("\n")
                stderr_buf.append(line)
                if not on_progress:
                    continue
                stripped = line.strip()
                if not (stripped.startswith("{") and stripped.endswith("}")):
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict) or "progress" not in obj:
                    continue
                try:
                    on_progress(obj)
                except Exception as cb_err:  # noqa: BLE001
                    stderr_buf.append(
                        f"[ddoc_runner] on_progress callback raised: {cb_err!r}"
                    )
        except Exception as read_err:  # noqa: BLE001
            stderr_buf.append(f"[ddoc_runner] stderr reader error: {read_err!r}")
        finally:
            try:
                stream.close()
            except Exception:  # noqa: BLE001
                pass

    t0 = time.monotonic()
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # line-buffered for live NDJSON consumption
    )

    reader = threading.Thread(
        target=_consume_stderr,
        args=(proc.stderr,),
        name="ddoc-stderr-reader",
        daemon=True,
    )
    reader.start()

    # Read stdout in the main thread (the reader thread owns stderr).
    # Using ``communicate()`` here would conflict with the reader on the
    # same Popen object — ``select`` sees stderr as a pipe to read, but
    # the reader thread has already taken it, producing EBADF.
    stdout_chunks: list[str] = []
    stdout_pipe = proc.stdout
    stdout_thread_err: list[str] = []

    def _drain_stdout() -> None:
        try:
            assert stdout_pipe is not None
            for chunk in stdout_pipe:
                stdout_chunks.append(chunk)
        except Exception as e:  # noqa: BLE001
            stdout_thread_err.append(repr(e))
        finally:
            try:
                if stdout_pipe is not None:
                    stdout_pipe.close()
            except Exception:  # noqa: BLE001
                pass

    stdout_reader = threading.Thread(
        target=_drain_stdout, name="ddoc-stdout-reader", daemon=True,
    )
    stdout_reader.start()

    timed_out = False
    try:
        proc.wait(timeout=timeout_eff)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        try:
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            pass

    stdout_reader.join(timeout=5.0)
    reader.join(timeout=2.0)
    stdout = "".join(stdout_chunks)
    if stdout_thread_err:
        stderr_buf.append(
            f"[ddoc_runner] stdout reader error(s): {stdout_thread_err}"
        )
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    stderr_tail = _tail("\n".join(stderr_buf))

    if timed_out:
        increment_counter("ddoc_cli_errors")
        raise DdocError(
            f"ddoc subprocess timed out after {timeout_eff}s",
            error_type="timeout",
            stderr_tail=stderr_tail,
            elapsed_ms=elapsed_ms,
            argv=argv,
        )

    increment_counter("ddoc_cli_calls")
    increment_counter("ddoc_cli_total_elapsed_ms", elapsed_ms)

    if proc.returncode != 0:
        increment_counter("ddoc_cli_errors")
        raise DdocError(
            f"ddoc subprocess exited {proc.returncode}",
            error_type="nonzero_exit",
            returncode=proc.returncode,
            stderr_tail=stderr_tail,
            elapsed_ms=elapsed_ms,
            argv=argv,
        )

    stdout = stdout or ""
    parsed: dict[str, Any] = {}
    parse_err: Optional[str] = None
    if require_json:
        if not stdout.strip():
            raise DdocError(
                "ddoc subprocess produced no stdout (expected --json envelope)",
                error_type="empty_stdout",
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
                elapsed_ms=elapsed_ms,
                argv=argv,
            )
        parsed_obj = _try_parse_last_json_object(stdout)
        if parsed_obj is None:
            raise DdocError(
                "ddoc subprocess stdout was not valid JSON",
                error_type="invalid_json",
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
                elapsed_ms=elapsed_ms,
                argv=argv,
            )
        parsed = parsed_obj
    else:
        parsed_obj = _try_parse_last_json_object(stdout)
        if parsed_obj is not None:
            parsed = parsed_obj
        else:
            parse_err = "stdout was not parseable as JSON (require_json=False)"

    return DdocResult(
        argv=argv,
        returncode=proc.returncode,
        stdout=stdout,
        stderr_tail=stderr_tail,
        elapsed_ms=elapsed_ms,
        json=parsed,
        json_parse_error=parse_err,
    )


# ── Helpers ────────────────────────────────────────────────────────────


def _tail(s: str, limit: int = STDERR_TAIL_BYTES) -> str:
    if not s:
        return ""
    if len(s) <= limit:
        return s
    return f"...[truncated {len(s) - limit} bytes]...\n" + s[-limit:]


def _try_parse_last_json_object(text: str) -> Optional[dict[str, Any]]:
    """Find the last brace-balanced JSON object in ``text`` and parse it.

    The CLI's ``--json`` mode emits exactly one object as the final
    line(s); but if any noise accidentally hits stdout (rich tags
    bleeding through, plugin print) we want to pick the JSON cleanly.
    Returns ``None`` if no parseable object is present.
    """
    s = text.strip()
    if not s:
        return None

    # Fast path: stdout is exactly one JSON object.
    if s.startswith("{") and s.endswith("}"):
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            pass

    # Fallback: scan from the end for a brace-balanced suffix.
    # We accept only objects (the contract is dict).
    depth = 0
    end = -1
    for i in range(len(s) - 1, -1, -1):
        ch = s[i]
        if ch == "}":
            if end == -1:
                end = i
            depth += 1
        elif ch == "{":
            depth -= 1
            if depth == 0:
                candidate = s[i:end + 1]
                try:
                    obj = json.loads(candidate)
                    return obj if isinstance(obj, dict) else None
                except json.JSONDecodeError:
                    end = -1
                    depth = 0
                    continue
    return None
