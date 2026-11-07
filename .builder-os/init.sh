#!/usr/bin/env bash
# init.sh — BUILDER-OS first-run bootstrap.
# Installs/provisions dependencies, runs the baseline verification gate, and
# reports the startup command. Idempotent: safe to re-run.
#
# Override for a real product repo:
#   INSTALL_CMD / VERIFY_CMD / START_CMD env vars, e.g.
#   INSTALL_CMD="npm install" VERIFY_CMD="npm test" ./init.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Commands must run in the PROJECT root, not in the folder holding this script.
# When init.sh lives inside a project's .builder-os/ state folder, that folder's
# parent IS the project root. When it sits at the BUILDER-OS root (the OS's own
# copy), the OS root is the project root. PROJECT_ROOT overrides both.
if [ "$(basename "$ROOT_DIR")" = ".builder-os" ]; then
  PROJECT_ROOT="${PROJECT_ROOT:-$(dirname "$ROOT_DIR")}"
else
  PROJECT_ROOT="${PROJECT_ROOT:-$ROOT_DIR}"
fi
cd "$PROJECT_ROOT"

export PYTHONDONTWRITEBYTECODE=1

# Defaults for ClaimShield Desk (Python 3.11+ FastAPI backend + pytest; Next.js cockpit in frontend/).
# Overridable per-project via env vars.
if [ -n "${INSTALL_CMD:-}" ]; then read -r -a INSTALL_CMD <<< "$INSTALL_CMD"; else INSTALL_CMD=(bash scripts/setup.sh); fi
if [ -n "${VERIFY_CMD:-}" ]; then read -r -a VERIFY_CMD <<< "$VERIFY_CMD"; else VERIFY_CMD=(bash scripts/verify.sh); fi
if [ -n "${START_CMD:-}" ]; then read -r -a START_CMD <<< "$START_CMD"; else START_CMD=(bash -c "source .venv/bin/activate && uvicorn backend.main:app --host 127.0.0.1 --port 8000"); fi

echo "==> Working directory: $PWD"
echo "==> Syncing dependencies"
"${INSTALL_CMD[@]}"

echo "==> Running baseline verification"
"${VERIFY_CMD[@]}"

echo "==> Startup command"
printf '    %q' "${START_CMD[@]}"
printf '\n'

if [ "${RUN_START_COMMAND:-0}" = "1" ]; then
  echo "==> Starting the app"
  exec "${START_CMD[@]}"
fi

echo "Set RUN_START_COMMAND=1 if you want init.sh to launch the app directly."
