"""Subprocess wrapper for ``ddoc serve`` to invoke the ddoc CLI.

ddoc-self-contained mirror of ``drift_studio/backend/app/services/
ddoc_runner.py`` (Round 6 / Phase 6). Living in the ddoc package
itself so ``ddoc serve`` works without the drift_studio backend
checked out. The two implementations are intentionally similar —
they can converge later, but for now keeping them separate avoids
ddoc taking a hard dependency on the backend layout.

Provides:

* ``run(args, ...)`` — synchronous, returns parsed JSON envelope.
* ``run_streamed(args, *, on_progress, ...)`` — Popen + stderr reader
  thread, yields NDJSON progress lines via callback. Used by the
  SSE endpoint.
* ``RunResult``, ``RunError`` — structured returns / exceptions.
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
from typing import Any, Callable, Dict, List, Optional


DEFAULT_TIMEOUT_SEC = float(os.getenv("DDOC_SERVE_DEFAULT_TIMEOUT_SEC", "600"))
STDERR_TAIL_BYTES = 4096


# ── Errors / Result ──────────────────────────────────────────────────


class RunError(Exception):
    """ddoc subprocess invocation failed.

    ``error_type`` is one of: ``timeout`` | ``nonzero_exit`` |
    ``invalid_json`` | ``empty_stdout``. Maps to HTTP 4xx/5xx in
    `app.py`.
    """

    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        returncode: Optional[int] = None,
        stderr_tail: str = "",
        elapsed_ms: Optional[int] = None,
        argv: Optional[List[str]] = None,
        json_partial: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.returncode = returncode
        self.stderr_tail = stderr_tail
        self.elapsed_ms = elapsed_ms
        self.argv = argv or []
        self.json_partial = json_partial

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "status": "error",
            "error_type": self.error_type,
            "message": str(self),
            "returncode": self.returncode,
            "stderr_tail": self.stderr_tail,
            "elapsed_ms": self.elapsed_ms,
            "argv": self.argv,
        }
        if self.json_partial is not None:
            out["error_envelope"] = self.json_partial
        return out


@dataclass
class RunResult:
    argv: List[str]
    returncode: int
    stdout: str
    stderr_tail: str
    elapsed_ms: int
    json: Dict[str, Any] = field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────


def _tail(s: str, limit: int = STDERR_TAIL_BYTES) -> str:
    if not s:
        return ""
    if len(s) <= limit:
        return s
    return f"...[truncated {len(s) - limit} bytes]...\n" + s[-limit:]


def _parse_last_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Mirror of backend's ``_try_parse_last_json_object``. Plugins
    sometimes leak banner lines onto stdout despite ``--quiet``;
    this picks the last brace-balanced object."""
    s = text.strip()
    if not s:
        return None
    if s.startswith("{") and s.endswith("}"):
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            pass
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


def _build_argv(args: List[str]) -> List[str]:
    """Hermetic invocation form — bind to current Python interpreter."""
    return [sys.executable, "-m", "ddoc.cli.main", *args]


# ── Public entry ──────────────────────────────────────────────────────


def run(
    args: List[str],
    *,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    env_extra: Optional[Dict[str, str]] = None,
    require_json: bool = True,
) -> RunResult:
    """Synchronous ddoc CLI invocation."""
    timeout_eff = timeout if timeout is not None else DEFAULT_TIMEOUT_SEC
    if timeout_eff <= 0:
        timeout_eff = None
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    argv = _build_argv(args)

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            argv, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout_eff, text=True,
        )
    except subprocess.TimeoutExpired as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        raise RunError(
            f"ddoc CLI timed out after {timeout_eff}s",
            error_type="timeout",
            stderr_tail=_tail((e.stderr or "")[-STDERR_TAIL_BYTES:] if isinstance(e.stderr, str) else ""),
            elapsed_ms=elapsed, argv=argv,
        ) from e

    elapsed = int((time.monotonic() - t0) * 1000)
    stderr_tail = _tail(proc.stderr or "")

    if proc.returncode != 0:
        # ddoc CLI emits structured error envelopes on stdout for known
        # failures (--json mode). Try to extract the envelope so callers
        # can route by error_code.
        partial = _parse_last_json_object(proc.stdout or "")
        raise RunError(
            f"ddoc CLI exited {proc.returncode}",
            error_type="nonzero_exit",
            returncode=proc.returncode,
            stderr_tail=stderr_tail,
            elapsed_ms=elapsed, argv=argv,
            json_partial=partial,
        )

    stdout = proc.stdout or ""
    if require_json:
        if not stdout.strip():
            raise RunError(
                "ddoc CLI produced no stdout (expected --json envelope)",
                error_type="empty_stdout",
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
                elapsed_ms=elapsed, argv=argv,
            )
        parsed = _parse_last_json_object(stdout)
        if parsed is None:
            raise RunError(
                "ddoc CLI stdout was not valid JSON",
                error_type="invalid_json",
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
                elapsed_ms=elapsed, argv=argv,
            )
    else:
        parsed = _parse_last_json_object(stdout) or {}

    return RunResult(
        argv=argv, returncode=proc.returncode,
        stdout=stdout, stderr_tail=stderr_tail,
        elapsed_ms=elapsed, json=parsed,
    )


ProgressCallback = Callable[[Dict[str, Any]], None]


def run_streamed(
    args: List[str],
    *,
    on_progress: Optional[ProgressCallback] = None,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    env_extra: Optional[Dict[str, str]] = None,
    require_json: bool = True,
    stderr_buffer_lines: int = 2048,
) -> RunResult:
    """Streaming variant — stderr NDJSON progress lines pumped to
    ``on_progress`` while the CLI runs. Otherwise identical contract
    to ``run``.
    """
    timeout_eff = timeout if timeout is not None else DEFAULT_TIMEOUT_SEC
    if timeout_eff <= 0:
        timeout_eff = None
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    argv = _build_argv(args)

    stderr_buf: deque = deque(maxlen=stderr_buffer_lines)

    def _drain_stderr(stream) -> None:
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
                    stderr_buf.append(f"[runner] on_progress raised: {cb_err!r}")
        finally:
            try:
                stream.close()
            except Exception:  # noqa: BLE001
                pass

    t0 = time.monotonic()
    proc = subprocess.Popen(
        argv, cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )
    reader = threading.Thread(
        target=_drain_stderr, args=(proc.stderr,),
        name="ddoc-serve-stderr-reader", daemon=True,
    )
    reader.start()

    # Read stdout in main thread to avoid clashing with reader on
    # ``communicate``.
    stdout_chunks: List[str] = []
    stdout_pipe = proc.stdout

    def _drain_stdout() -> None:
        try:
            assert stdout_pipe is not None
            for chunk in stdout_pipe:
                stdout_chunks.append(chunk)
        finally:
            try:
                if stdout_pipe is not None:
                    stdout_pipe.close()
            except Exception:  # noqa: BLE001
                pass

    stdout_reader = threading.Thread(
        target=_drain_stdout, name="ddoc-serve-stdout-reader", daemon=True,
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
    elapsed = int((time.monotonic() - t0) * 1000)
    stdout = "".join(stdout_chunks)
    stderr_tail = _tail("\n".join(stderr_buf))

    if timed_out:
        raise RunError(
            f"ddoc CLI timed out after {timeout_eff}s",
            error_type="timeout",
            stderr_tail=stderr_tail, elapsed_ms=elapsed, argv=argv,
        )

    if proc.returncode != 0:
        partial = _parse_last_json_object(stdout)
        raise RunError(
            f"ddoc CLI exited {proc.returncode}",
            error_type="nonzero_exit",
            returncode=proc.returncode, stderr_tail=stderr_tail,
            elapsed_ms=elapsed, argv=argv, json_partial=partial,
        )

    if require_json:
        parsed = _parse_last_json_object(stdout)
        if parsed is None:
            raise RunError(
                "ddoc CLI stdout was not valid JSON",
                error_type="invalid_json" if stdout.strip() else "empty_stdout",
                returncode=proc.returncode,
                stderr_tail=stderr_tail, elapsed_ms=elapsed, argv=argv,
            )
    else:
        parsed = _parse_last_json_object(stdout) or {}

    return RunResult(
        argv=argv, returncode=proc.returncode,
        stdout=stdout, stderr_tail=stderr_tail,
        elapsed_ms=elapsed, json=parsed,
    )
