#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment at .venv..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# Try installing hindsight-client, but never fail if it fails
echo "Attempting to install hindsight-client..."
if pip install hindsight-client; then
    echo "hindsight-client installed successfully."
else
    echo "Notice: hindsight-client install failed or skipped; continuing with httpx fallback."
fi
