#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "${CONDA_DEFAULT_ENV:-}" == "gear-copilot" ]]; then
  PYTHON="$(command -v python)"
elif command -v conda >/dev/null 2>&1; then
  PYTHON="$(conda run -n gear-copilot which python 2>/dev/null || true)"
else
  PYTHON=""
fi

if [[ -z "$PYTHON" || ! -x "$PYTHON" ]]; then
  echo "Python-Interpreter für Conda-Env 'gear-copilot' nicht gefunden." >&2
  echo "Erstelle zuerst das Env: conda env create -f cad_processor/environment.yml" >&2
  echo "Starte danach mit: conda activate gear-copilot && ./scripts/start_local.sh" >&2
  exit 1
fi

pkill -f "uvicorn app.api.main" 2>/dev/null || true
pkill -f "uvicorn src.main" 2>/dev/null || true

HOST="${GEAR_COPILOT_HOST:-127.0.0.1}"
PORT="${GEAR_COPILOT_PORT:-8000}"

UVICORN_ARGS=(app.api.main:app --host "$HOST" --port "$PORT")
if [[ "${GEAR_COPILOT_RELOAD:-0}" == "1" ]]; then
  UVICORN_ARGS+=(--reload)
fi

exec "$PYTHON" -m uvicorn "${UVICORN_ARGS[@]}"
