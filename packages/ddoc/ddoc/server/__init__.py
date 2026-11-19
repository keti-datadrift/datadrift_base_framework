"""ddoc REST facade — `ddoc serve`.

Wraps the ddoc CLI (every analyze / report / export /
examples / fetch / plugin command) behind a thin FastAPI server so
external systems and scripted automation can call ddoc over HTTP
without spawning subprocesses themselves.

The default port is **8765**, chosen to avoid colliding with common
application servers on 8000.
"""
from .app import create_app  # noqa: F401
