"""File-backed write-token store (Round 24).

Single JSON file at ``<library_dir>/.tokens.json`` holding non-revoked
write credentials. Only the SHA-256 hash of each secret is persisted;
the plaintext is returned **once** at creation time and is never
recoverable from the store. This keeps file leaks from compromising
active tokens.

Schema (forward-compat ``version`` field):

.. code-block:: json

   {
     "version": 1,
     "tokens": [
       {
         "id": "tok_<8 hex>",
         "name": "ci",
         "scope": "write",
         "secret_hash": "<sha256 hex>",
         "created_at": "2026-05-09T01:23:45Z",
         "revoked_at": null
       }
     ]
   }

The store coexists with ``DDOC_RECIPES_WRITE_TOKEN`` (single env
secret, Round 22) — a write request is accepted if its header value
matches *either* the env secret *or* the hash of any active token.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_TOKEN_FILE = ".tokens.json"
_VERSION = 1
_LOCK = threading.Lock()


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(base: Path) -> Path:
    return base / _TOKEN_FILE


def load(base: Path) -> Dict[str, Any]:
    """Load the token file. Returns an empty store if missing."""
    p = _path(base)
    if not p.exists():
        return {"version": _VERSION, "tokens": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "tokens" not in data:
            return {"version": _VERSION, "tokens": []}
        return data
    except Exception:
        return {"version": _VERSION, "tokens": []}


def _save(base: Path, store: Dict[str, Any]) -> None:
    p = _path(base)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(store, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)
    try:
        os.chmod(p, 0o600)
    except Exception:  # noqa: BLE001
        pass


def public_view(token: Dict[str, Any]) -> Dict[str, Any]:
    """Strip the secret_hash so a token can be returned over the wire."""
    return {
        "id": token["id"],
        "name": token.get("name", ""),
        "scope": token.get("scope", "write"),
        "created_at": token.get("created_at"),
        "revoked_at": token.get("revoked_at"),
    }


def list_tokens(base: Path) -> List[Dict[str, Any]]:
    return [public_view(t) for t in load(base).get("tokens", [])]


def has_any_active(base: Path) -> bool:
    return any(t.get("revoked_at") is None for t in load(base).get("tokens", []))


def is_initialized(base: Path) -> bool:
    """True if the token store file exists at all. Once a deployment
    has created any token, the gate stays on even if every token is
    later revoked — otherwise revoking the last token would
    accidentally re-open writes to anonymous callers."""
    return _path(base).exists()


def create_token(base: Path, name: str, scope: str = "write") -> Dict[str, Any]:
    """Mint a new token. Returns ``{id, secret, name, scope, created_at}``
    — the secret is plaintext and visible *only* in this response."""
    secret = secrets.token_urlsafe(32)
    tok_id = "tok_" + secrets.token_hex(4)
    record = {
        "id": tok_id,
        "name": name,
        "scope": scope,
        "secret_hash": _hash_secret(secret),
        "created_at": _now_iso(),
        "revoked_at": None,
    }
    with _LOCK:
        store = load(base)
        store["version"] = _VERSION
        store.setdefault("tokens", []).append(record)
        _save(base, store)
    return {
        "id": tok_id,
        "name": name,
        "scope": scope,
        "secret": secret,
        "created_at": record["created_at"],
    }


def revoke_token(base: Path, tok_id: str) -> Optional[Dict[str, Any]]:
    """Mark a token as revoked. Returns the updated record or None
    when no such token exists."""
    with _LOCK:
        store = load(base)
        for t in store.get("tokens", []):
            if t.get("id") == tok_id:
                if t.get("revoked_at") is None:
                    t["revoked_at"] = _now_iso()
                _save(base, store)
                return public_view(t)
    return None


def verify(base: Path, secret_plaintext: str) -> bool:
    """True iff ``secret_plaintext`` matches a non-revoked token in the
    store. Constant-time per token via hashlib comparison."""
    if not secret_plaintext:
        return False
    candidate = _hash_secret(secret_plaintext)
    for t in load(base).get("tokens", []):
        if t.get("revoked_at") is not None:
            continue
        stored = t.get("secret_hash", "")
        if secrets.compare_digest(candidate, stored):
            return True
    return False
