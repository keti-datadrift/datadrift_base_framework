#!/usr/bin/env bash
# End-to-end integration demo: an application and ddoc exchange data and
# a drift report without sharing any Python code.
#
#   examples/app-integration/run.sh
#
# Requires ddoc on PATH (pip install -e ddoc). Uses only the ddoc core.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work="${WORK_DIR:-$(mktemp -d)}"
port="${RECEIVER_PORT:-8090}"
key="demo-key"
py="${PYTHON:-python3}"

echo "work dir: $work"

# 0. The application's side: its data, and an endpoint for reports.
"$py" "$here/make_data.py" "$work/source"
"$py" "$here/receiver.py" --port "$port" --api-key "$key" --out "$work/received" &
receiver=$!
trap 'kill $receiver 2>/dev/null || true' EXIT
sleep 1

# 1. Bring the data in. file:// is built in; s3://, gs://, http(s)://
#    come from plugins through the same command.
ddoc fetch "file://$work/source/baseline" --dest "$work/data/baseline" --json > /dev/null
ddoc fetch "file://$work/source/today" --dest "$work/data/today" --json > /dev/null

# 2. Judge it. The exit code is the verdict (0 OK, 1 DRIFT, 2 BLIND).
set +e
ddoc diff "$work/data/baseline" "$work/data/today" --json > "$work/result.json"
verdict_code=$?
set -e
echo "ddoc diff exit code: $verdict_code"

# 3. Ship the result to the application as a DriftReport envelope.
ddoc export drift-report "$work/result.json" --to http --json \
  --config "{\"base_url\": \"http://127.0.0.1:$port\", \"api_key\": \"$key\",
             \"source\": {\"app_id\": \"demo-app\", \"app_type\": \"example\"}}" > /dev/null

sleep 0.5
echo "reports stored by the application:"
ls "$work/received"
