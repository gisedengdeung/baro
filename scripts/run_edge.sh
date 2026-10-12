#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

EDGE_ENV_FILE="${EDGE_ENV_FILE:-$ROOT_DIR/.env.edge}"
if [ -f "$EDGE_ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$EDGE_ENV_FILE"
  set +a
fi

python -m edge.main \
  --camera "${EDGE_CAMERA_SOURCE:-0}" \
  --serial "${EDGE_SERIAL_PORT:-/dev/ttyUSB0}" \
  --cloud-url "${CLOUD_BASE_URL:-http://localhost:8000}" \
  --edge-id "${EDGE_ID:-edge-default}" \
  "$@"
