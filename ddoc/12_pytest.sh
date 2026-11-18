#!/usr/bin/env bash
# Run the active test suite. The legacy `test_cli_golden.py` is currently
# parked as `__test_cli_golden.py` (disabled prefix); do not re-add it
# here until it is reintroduced.
#
# Self-activates the project's local venv so plugin packages
# (ddoc-plugin-categorical, ddoc-plugin-tabular, ...) — installed only
# inside that venv — are importable. Without this, pytest from the
# system Python fails to collect plugin tests with ModuleNotFoundError.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Skip activation if a venv is already active.
if [ -z "${VIRTUAL_ENV:-}" ]; then
    if [ -f "${SCRIPT_DIR}/.venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "${SCRIPT_DIR}/.venv/bin/activate"
    elif [ -f "${SCRIPT_DIR}/venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "${SCRIPT_DIR}/venv/bin/activate"
    else
        echo "Error: no .venv/ or venv/ found at ${SCRIPT_DIR}." >&2
        echo "Run: bash 01_make_venv.sh && source .venv/bin/activate &&" >&2
        echo "     bash 03_install_ddoc.sh && bash 11_install_pytest.sh" >&2
        exit 1
    fi
fi

pytest tests/ -v
