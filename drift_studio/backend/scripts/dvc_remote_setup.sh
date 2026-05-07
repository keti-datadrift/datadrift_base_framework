#!/usr/bin/env bash
# Phase 4 — DVC remote bootstrap.
#
# Reads two env vars:
#   DVC_REMOTE_URL   e.g. s3://bucket/drift_studio  or  /mnt/dvc-share
#   DVC_SITE_ID      e.g. site_a                   (used as a path prefix)
# and configures a default DVC remote pointing at
#   <DVC_REMOTE_URL>/<DVC_SITE_ID>/
#
# Recommended layout under that root:
#   <DVC_SITE_ID>/datasets/   (raw + curated input data)
#   <DVC_SITE_ID>/models/     (trained model artifacts)
#   <DVC_SITE_ID>/audit/      (keti_veritas-style envelope JSON)
#
# Idempotent — safe to run on every container start. Logs and exits 0
# even on partial failure so backend startup is not blocked.

set -u

SCRIPT_NAME="dvc_remote_setup"

log() { echo "[$SCRIPT_NAME] $*"; }

if [ -z "${DVC_REMOTE_URL:-}" ]; then
  log "DVC_REMOTE_URL not set — skipping remote setup"
  exit 0
fi

SITE_ID="${DVC_SITE_ID:-default}"
REMOTE_NAME="${DVC_REMOTE_NAME:-origin}"
REMOTE_ROOT="${DVC_REMOTE_URL%/}/$SITE_ID"

# Ensure DVC is initialized (no-op if already present).
if [ ! -d ".dvc" ]; then
  log "no .dvc directory found in $(pwd) — running 'dvc init --no-scm'"
  if ! dvc init --no-scm >/dev/null 2>&1; then
    log "dvc init failed — refusing to configure remote on uninitialized repo"
    exit 0
  fi
fi

log "configuring remote '$REMOTE_NAME' -> $REMOTE_ROOT"
if ! dvc remote add -d -f "$REMOTE_NAME" "$REMOTE_ROOT" >/dev/null 2>&1; then
  log "WARN: 'dvc remote add' returned non-zero; continuing"
fi

# For local-FS remotes, eagerly mkdir the recommended subtree.
case "$DVC_REMOTE_URL" in
  s3://*|gs://*|azure://*|ssh://*|http://*|https://*)
    log "remote is a network URL — skipping local mkdir"
    ;;
  *)
    for sub in datasets models audit; do
      mkdir -p "$REMOTE_ROOT/$sub" 2>/dev/null || true
    done
    log "ensured local remote subtree at $REMOTE_ROOT"
    ;;
esac

log "done"
exit 0
