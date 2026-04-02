#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

VENV_PATH=".venv-cloud"
PYTHON_BIN=""

usage() {
  cat <<'USAGE'
Usage: ./scripts/setup_cloud.sh [--venv-path <path>] [--python <bin>]

Options:
  --venv-path <path>  Override virtualenv path (default: .venv-cloud)
  --python <bin>      Use a specific Python binary
  -h, --help          Show this help message
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv-path)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --venv-path requires a value." >&2
        exit 1
      fi
      VENV_PATH="$2"
      shift 2
      ;;
    --python)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --python requires a value." >&2
        exit 1
      fi
      PYTHON_BIN="$2"
      shift 2
      ;;
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

if [[ -n "$PYTHON_BIN" ]]; then
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "[ERROR] Python binary not found: $PYTHON_BIN" >&2
    exit 1
  fi
else
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "[ERROR] Python not found. Install python3 (or python) and retry." >&2
  exit 1
fi

if [[ ! -d "$VENV_PATH" ]]; then
  echo "[INFO] Creating virtualenv: $VENV_PATH"
  "$PYTHON_BIN" -m venv "$VENV_PATH"
else
  echo "[INFO] Reusing existing virtualenv: $VENV_PATH"
fi

if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  echo "[ERROR] Invalid virtualenv: $VENV_PATH/bin/python not found." >&2
  exit 1
fi

echo "[INFO] Upgrading pip in $VENV_PATH"
"$VENV_PATH/bin/python" -m pip install --upgrade pip

echo "[INFO] Installing Cloud dependencies"
"$VENV_PATH/bin/pip" install -r requirements-cloud.txt

if [[ ! -f "$ROOT_DIR/.env.cloud" && -f "$ROOT_DIR/.env.cloud.example" ]]; then
  cp "$ROOT_DIR/.env.cloud.example" "$ROOT_DIR/.env.cloud"
  echo "[INFO] Created .env.cloud from .env.cloud.example"
else
  echo "[INFO] Keeping existing .env.cloud (not overwritten)"
fi

cat <<EOF
[DONE] Cloud setup completed.

Next:
  source $VENV_PATH/bin/activate
  ./scripts/run_cloud.sh
EOF
