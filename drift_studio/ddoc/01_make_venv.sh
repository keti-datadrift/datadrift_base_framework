#!/usr/bin/env bash
# Create the project's local virtualenv at .venv/. Subsequent
# scripts (`03_install_ddoc.sh`, `11_install_pytest.sh`,
# `12_pytest.sh`) will detect and activate it automatically.
#
# Convention: the venv directory is `.venv/` (modern Python tooling
# default; matches what's already installed on this checkout). After
# this script:
#
#   source .venv/bin/activate
#   bash 03_install_ddoc.sh
#   bash 11_install_pytest.sh
#   bash 12_pytest.sh   # (auto-activates if venv not active)
set -e

if [ -d .venv ]; then
    echo ".venv/ already exists — skipping creation."
else
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
echo
echo "✓ .venv/ ready. Next:"
echo "    source .venv/bin/activate && bash 03_install_ddoc.sh"
