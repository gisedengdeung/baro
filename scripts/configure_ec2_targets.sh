#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EDGE_ENV_FILE="${EDGE_ENV_FILE:-$ROOT_DIR/.env.edge}"
FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE:-$ROOT_DIR/frontend/simple-video-viewer/.env}"
EC2_IP="${EC2_IP:-}"

usage() {
  cat <<'USAGE'
Usage: ./scripts/configure_ec2_targets.sh --ip <EC2_PUBLIC_IP> [--edge-env <path>] [--frontend-env <path>]

Options:
  --ip <IP>            EC2 public IPv4 address (required)
  --edge-env <path>    Edge env file path (default: .env.edge)
  --frontend-env <path> Frontend env file path (default: frontend/simple-video-viewer/.env)
  -h, --help           Show this help message
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ip)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --ip requires a value." >&2
        exit 1
      fi
      EC2_IP="$2"
      shift 2
      ;;
    --edge-env)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --edge-env requires a value." >&2
        exit 1
      fi
      EDGE_ENV_FILE="$2"
      shift 2
      ;;
    --frontend-env)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --frontend-env requires a value." >&2
        exit 1
      fi
      FRONTEND_ENV_FILE="$2"
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

if [[ -z "$EC2_IP" ]]; then
  echo "[ERROR] Missing --ip <EC2_PUBLIC_IP>" >&2
  usage
  exit 1
fi

if ! [[ "$EC2_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  echo "[ERROR] Invalid IPv4 format: $EC2_IP" >&2
  exit 1
fi

upsert_key() {
  local file="$1"
  local key="$2"
  local value="$3"
  local dir
  local escaped
  escaped=$(printf '%s\n' "$value" | sed 's/[\/&]/\\&/g')
  dir="$(dirname "$file")"
  mkdir -p "$dir"

  if [[ ! -f "$file" ]]; then
    touch "$file"
  fi

  if grep -q "^${key}=" "$file"; then
    sed -i "s/^${key}=.*/${key}=${escaped}/" "$file"
  else
    printf "%s=%s\n" "$key" "$value" >>"$file"
  fi
}

EDGE_URL="http://${EC2_IP}"
WS_URL="ws://${EC2_IP}"

upsert_key "$EDGE_ENV_FILE" "CLOUD_BASE_URL" "$EDGE_URL"
upsert_key "$FRONTEND_ENV_FILE" "REACT_APP_API_BASE_URL" "$EDGE_URL"
upsert_key "$FRONTEND_ENV_FILE" "REACT_APP_WS_BASE_URL" "$WS_URL"

cat <<EOF
[DONE] Updated client targets to EC2.

Edge:
  $EDGE_ENV_FILE
  CLOUD_BASE_URL=$EDGE_URL

Frontend:
  $FRONTEND_ENV_FILE
  REACT_APP_API_BASE_URL=$EDGE_URL
  REACT_APP_WS_BASE_URL=$WS_URL

Next:
  1) Restart cloud/edge/frontend processes
  2) Verify from local browser: http://${EC2_IP}/docs
EOF
