"""ddoc REST facade — `ddoc serve`.

Round 14 — wraps the ddoc CLI (every analyze / report / export /
examples / fetch / plugin command) behind a thin FastAPI server so
external systems and scripted automation can call ddoc over HTTP
without spawning subprocesses themselves.

Coexists with ``drift_studio/backend`` (port 8000); the recommended
default port here is **8765** to avoid collision. The backend is a
larger orchestration monolith that already wraps a subset of ddoc;
``ddoc serve`` is the *self-contained* facade ddoc itself ships, with
no dependency on drift_studio.
"""
from .app import create_app  # noqa: F401
