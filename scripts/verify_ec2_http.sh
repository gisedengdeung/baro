#!/usr/bin/env bash
set -euo pipefail

TARGET_HOST="${TARGET_HOST:-}"
SCHEME="${SCHEME:-https}"
TIMEOUT_SEC="${TIMEOUT_SEC:-5}"
CHECK_8000="${CHECK_8000:-false}"

usage() {
  cat <<'USAGE'
Usage: ./scripts/verify_ec2_http.sh --host <DOMAIN_OR_IP> [--scheme https|http] [--timeout <sec>] [--check-8000]

Checks:
  - <scheme>://<host>/
  - <scheme>://<host>/docs
  - optional: http://<host>:8000/
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host|--ip)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] $1 requires a value." >&2
        exit 1
      fi
      TARGET_HOST="$2"
      shift 2
      ;;
    --scheme)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --scheme requires a value." >&2
        exit 1
      fi
      SCHEME="$2"
      shift 2
      ;;
    --timeout)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --timeout requires a value." >&2
        exit 1
      fi
      TIMEOUT_SEC="$2"
      shift 2
      ;;
    --check-8000)
      CHECK_8000="true"
      shift
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

if [[ -z "$TARGET_HOST" ]]; then
  echo "[ERROR] Missing --host <DOMAIN_OR_IP>" >&2
  usage
  exit 1
fi

check_url() {
  local label="$1"
  local url="$2"
  local http_code
  http_code="$(curl -sS -o /dev/null -m "$TIMEOUT_SEC" -w "%{http_code}" "$url" || true)"
  if [[ "$http_code" =~ ^[23][0-9][0-9]$ ]]; then
    echo "[PASS] $label: $url (HTTP $http_code)"
  else
    echo "[WARN] $label: $url (HTTP $http_code)"
  fi
}

echo "[INFO] Verifying $TARGET_HOST via $SCHEME"
check_url "root" "$SCHEME://$TARGET_HOST/"
check_url "FastAPI docs" "$SCHEME://$TARGET_HOST/docs"

if [[ "$CHECK_8000" == "true" ]]; then
  check_url "direct 8000 (should be blocked on public net)" "http://$TARGET_HOST:8000/"
fi
