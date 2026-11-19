#!/usr/bin/env bash
# Plain-shell drift gate for any CI system.
#
#   examples/ci-gate/gate.sh <baseline> <incoming> [report.html]
#
# Exit code is ddoc's verdict: 0 OK, 1 DRIFT, 2 BLIND (cannot judge).
# Requires ddoc on PATH (pip install -e packages/ddoc, or pip install ./packages/ddoc).
set -u

ref="${1:?usage: gate.sh <baseline> <incoming> [report.html]}"
cur="${2:?usage: gate.sh <baseline> <incoming> [report.html]}"
report="${3:-}"

args=(diff "$ref" "$cur")
if [ -n "$report" ]; then
  args+=(--report "$report")
fi

ddoc "${args[@]}"
code=$?

case "$code" in
  0) echo "drift gate: OK" ;;
  1) echo "drift gate: DRIFT — blocking" ;;
  2) echo "drift gate: BLIND — ddoc could not judge this data; blocking" ;;
  *) echo "drift gate: ddoc failed with exit code $code" ;;
esac
exit "$code"
