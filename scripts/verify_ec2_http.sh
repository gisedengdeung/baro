#!/usr/bin/env bash
set -euo pipefail

EC2_IP="${EC2_IP:-}"
TIMEOUT_SEC="${TIMEOUT_SEC:-5}"

usage() {
  cat <<'USAGE'
Usage: ./scripts/verify_ec2_http.sh --ip <EC2_PUBLIC_IP> [--timeout <sec>]

Checks:
  - http://<EC2_IP>/ (via nginx)
  - http://<EC2_IP>/docs (FastAPI docs page)
  - http://<EC2_IP>:8000/ (direct uvicorn check; optional if SG allows)
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
    --timeout)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --timeout requires a value." >&2
        exit 1
      fi
      TIMEOUT_SEC="$2"
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

echo "[INFO] Checking EC2 HTTP endpoints for $EC2_IP"
check_url "nginx root" "http://$EC2_IP/"
check_url "FastAPI docs" "http://$EC2_IP/docs"
check_url "direct :8000 (temporary check)" "http://$EC2_IP:8000/"

cat <<EOF
[DONE] HTTP checks complete.
If :8000 is open only for bootstrap tests, close inbound 8000 after verification.
EOF
