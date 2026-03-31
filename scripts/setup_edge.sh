#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

VENV_PATH=".venv-edge"
PYTHON_BIN=""
EDGE_ENV_FILE="$ROOT_DIR/.env.edge"

usage() {
  cat <<'USAGE'
Usage: ./scripts/setup_edge.sh [--venv-path <path>] [--python <bin>]

Options:
  --venv-path <path>  Override virtualenv path (default: .venv-edge)
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

read -r PY_MAJOR PY_MINOR < <("$PYTHON_BIN" - <<'PY'
import sys
print(sys.version_info.major, sys.version_info.minor)
PY
)

if (( PY_MAJOR != 3 || PY_MINOR < 10 || PY_MINOR > 11 )); then
  echo "[ERROR] Edge setup requires Python 3.10 or 3.11. Current: $PY_MAJOR.$PY_MINOR" >&2
  echo "        Try: ./scripts/setup_edge.sh --python python3.11" >&2
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

echo "[INFO] Upgrading pip/setuptools/wheel in $VENV_PATH"
"$VENV_PATH/bin/python" -m pip install --upgrade pip setuptools wheel

echo "[INFO] Installing Edge dependencies"
"$VENV_PATH/bin/pip" install -r requirements-edge.txt

if [[ ! -f "$EDGE_ENV_FILE" && -f "$ROOT_DIR/.env.edge.example" ]]; then
  cp "$ROOT_DIR/.env.edge.example" "$EDGE_ENV_FILE"
  echo "[INFO] Created .env.edge from .env.edge.example"
else
  echo "[INFO] Keeping existing .env.edge (not overwritten)"
fi

PERSON_MODEL_PATH="edge/models/yolov8n.pt"
FALL_MODEL_PATH="edge/models/fall_det_1.pt"

if [[ -f "$EDGE_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$EDGE_ENV_FILE"
  set +a
  PERSON_MODEL_PATH="${EDGE_PERSON_MODEL_PATH:-$PERSON_MODEL_PATH}"
  FALL_MODEL_PATH="${EDGE_FALL_MODEL_PATH:-$FALL_MODEL_PATH}"
fi

if [[ -z "${EDGE_SHARED_SECRET:-}" ]]; then
  echo "[WARN] EDGE_SHARED_SECRET is empty in $EDGE_ENV_FILE"
fi

check_model_file() {
  local label="$1"
  local path="$2"
  local -a candidates=()
  local candidate=""

  if [[ "$path" == /* ]]; then
    candidates=("$path")
  elif [[ "$path" == */* ]]; then
    candidates=("$ROOT_DIR/$path")
  else
    candidates=("$ROOT_DIR/edge/models/$path" "$ROOT_DIR/$path")
  fi

  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      echo "[INFO] $label model found: $path -> $candidate"
      return
    fi
  done

  echo "[WARN] $label model missing: $path"
  if [[ "${#candidates[@]}" -gt 0 ]]; then
    echo "       checked: ${candidates[*]}"
  fi
}

check_model_file "Person" "$PERSON_MODEL_PATH"
check_model_file "Fall" "$FALL_MODEL_PATH"

cat <<EOF
[DONE] Edge setup completed.

Next:
  source $VENV_PATH/bin/activate
  python3 -m edge.main --camera 0 --serial /dev/ttyUSB0 --cloud-url http://localhost:8000 --edge-id edge-default
  # or:
  ./scripts/run_edge.sh
EOF
