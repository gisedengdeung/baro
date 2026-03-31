#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EDGE_ENV_FILE="${EDGE_ENV_FILE:-$ROOT_DIR/.env.edge}"
FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE:-$ROOT_DIR/frontend/simple-video-viewer/.env}"

PUBLIC_HOST="${PUBLIC_HOST:-}"
PUBLIC_SCHEME="${PUBLIC_SCHEME:-https}"
EDGE_HOST="${EDGE_HOST:-}"
EDGE_SCHEME="${EDGE_SCHEME:-http}"

usage() {
  cat <<'USAGE'
Usage: ./scripts/configure_ec2_targets.sh --public-host <DOMAIN_OR_IP> --edge-host <TAILSCALE_IP_OR_HOST> [options]

Options:
  --public-host <host>    Browser-facing host/domain for frontend API/WS env
  --edge-host <host>      Edge-facing host (typically Tailscale IP)
  --public-scheme <s>     https|http (default: https)
  --edge-scheme <s>       http|https (default: http)
  --edge-env <path>       Edge env file path (default: .env.edge)
  --frontend-env <path>   Frontend env file path (default: frontend/simple-video-viewer/.env)
  --ip <host>             Legacy shortcut: sets both public-host and edge-host
  -h, --help              Show this help message
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --public-host)
      PUBLIC_HOST="$2"
      shift 2
      ;;
    --edge-host)
      EDGE_HOST="$2"
      shift 2
      ;;
    --public-scheme)
      PUBLIC_SCHEME="$2"
      shift 2
      ;;
    --edge-scheme)
      EDGE_SCHEME="$2"
      shift 2
      ;;
    --edge-env)
      EDGE_ENV_FILE="$2"
      shift 2
      ;;
    --frontend-env)
      FRONTEND_ENV_FILE="$2"
      shift 2
      ;;
    --ip)
      PUBLIC_HOST="$2"
      EDGE_HOST="$2"
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

if [[ -z "$PUBLIC_HOST" || -z "$EDGE_HOST" ]]; then
  echo "[ERROR] --public-host and --edge-host are required" >&2
  usage
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

EDGE_URL="${EDGE_SCHEME}://${EDGE_HOST}"
API_URL="${PUBLIC_SCHEME}://${PUBLIC_HOST}"
WS_URL="${API_URL/http/ws}"

upsert_key "$EDGE_ENV_FILE" "CLOUD_BASE_URL" "$EDGE_URL"
upsert_key "$FRONTEND_ENV_FILE" "REACT_APP_API_BASE_URL" "$API_URL"
upsert_key "$FRONTEND_ENV_FILE" "REACT_APP_WS_BASE_URL" "$WS_URL"

cat <<EOF
[DONE] Updated targets.

Edge:
  $EDGE_ENV_FILE
  CLOUD_BASE_URL=$EDGE_URL

Frontend:
  $FRONTEND_ENV_FILE
  REACT_APP_API_BASE_URL=$API_URL
  REACT_APP_WS_BASE_URL=$WS_URL

Next:
  1) Restart Edge and Frontend processes
  2) Verify browser access: $API_URL/docs
EOF
