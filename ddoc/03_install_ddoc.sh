#!/usr/bin/env bash
# Editable-install the core ddoc package + every plugin in plugins/.
# Modality plugins (vision, text, timeseries, audio) and the
# load-bearing extras added in ddoc Rounds 26-A / 27-B
# (categorical, tabular) all need to be importable for the test
# suite — without this loop, `pytest` fails at collection time
# with `ModuleNotFoundError: No module named 'ddoc_plugin_categorical'`
# (the bug originally reported 2026-05-10).
#
# Run inside an active venv. `01_make_venv.sh` creates `.venv/`;
# `12_pytest.sh` self-activates if needed.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Auto-activate the local venv if not already inside one.
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# Clean stale build artifacts that confuse editable installs.
rm -rf build/ dist/ ddoc.egg-info

pip install --upgrade pip

# Core ddoc package (editable).
pip install --no-cache-dir -e .

# Every plugin under plugins/ (excluding the meta-package "ddoc-full"
# which only declares deps and doesn't itself need an editable install).
for plugin_dir in plugins/ddoc-plugin-*/; do
    if [ -f "${plugin_dir}/pyproject.toml" ]; then
        echo "→ installing ${plugin_dir}"
        pip install --no-cache-dir -e "${plugin_dir}"
    fi
done

echo
echo "✓ ddoc + plugins installed (editable). Run: bash 12_pytest.sh"
