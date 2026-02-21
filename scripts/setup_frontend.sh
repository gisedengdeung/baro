#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend/simple-video-viewer"
FRONTEND_ENV_FILE="$FRONTEND_DIR/.env"
CACHE_DIR="${FRONTEND_NPM_CACHE_DIR:-$FRONTEND_DIR/.npm-cache}"

usage() {
  cat <<'USAGE'
Usage: ./scripts/setup_frontend.sh

Options:
  -h, --help  Show this help message
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v node >/dev/null 2>&1; then
  echo "[ERROR] node not found. Install Node.js and retry." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[ERROR] npm not found. Install npm and retry." >&2
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "[ERROR] Frontend directory not found: $FRONTEND_DIR" >&2
  exit 1
fi

cd "$FRONTEND_DIR"

mkdir -p "$CACHE_DIR"
echo "[INFO] Using npm cache: $CACHE_DIR"
echo "[INFO] Installing frontend dependencies"
npm install --cache "$CACHE_DIR"

if [[ ! -f "$FRONTEND_ENV_FILE" ]]; then
  cat >"$FRONTEND_ENV_FILE" <<'EOF'
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_BASE_URL=ws://localhost:8000
REACT_APP_EDGE_ID=edge-default
EOF
  echo "[INFO] Created frontend .env with default values"
else
  echo "[INFO] Keeping existing frontend .env (not overwritten)"
fi

cat <<EOF
[DONE] Frontend setup completed.

Next:
  cd $FRONTEND_DIR
  npm start
EOF
