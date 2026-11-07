#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if [ ! -f ".venv/bin/python" ]; then
    echo "Virtual environment .venv missing. Please run scripts/setup.sh first."
    exit 1
fi

exec .venv/bin/python -m pytest -q
