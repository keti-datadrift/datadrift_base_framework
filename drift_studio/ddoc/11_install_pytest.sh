#!/usr/bin/env bash
# Editable install with the [test] extras (pytest, pytest-asyncio, ...).
# Self-activates the project's local venv if not already inside one,
# matching `12_pytest.sh`'s behaviour.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [ -z "${VIRTUAL_ENV:-}" ] && [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

pip install -e ".[test]"
