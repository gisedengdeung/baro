#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

for candidate in "$ROOT_DIR/.env.cloud" "$ROOT_DIR/.env"; do
  if [[ -f "$candidate" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$candidate"
    set +a
    break
  fi
done

uvicorn cloud.main:app --host 0.0.0.0 --port 8000
