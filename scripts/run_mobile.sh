#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT_DIR/mobile/flutter/app"
PLATFORM="android"
API_BASE_URL=""

usage() {
  cat <<'USAGE'
Usage: ./scripts/run_mobile.sh [--platform android|ios] [--api-base-url URL]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      PLATFORM="${2:-}"
      shift 2
      ;;
    --api-base-url)
      API_BASE_URL="${2:-}"
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

if ! command -v flutter >/dev/null 2>&1; then
  echo "[ERROR] flutter not found. Install Flutter SDK first." >&2
  exit 1
fi

if [[ ! -d "$APP_DIR/android" || ! -d "$APP_DIR/ios" ]]; then
  echo "[INFO] Platform folders missing. Running setup first."
  "$ROOT_DIR/scripts/setup_mobile.sh"
fi

cd "$APP_DIR"

if [[ -z "$API_BASE_URL" ]]; then
  if [[ "$PLATFORM" == "android" ]]; then
    API_BASE_URL="http://10.0.2.2:8000"
  else
    API_BASE_URL="http://127.0.0.1:8000"
  fi
fi

if [[ "$PLATFORM" == "android" ]]; then
  flutter run -d android --dart-define "API_BASE_URL=$API_BASE_URL"
elif [[ "$PLATFORM" == "ios" ]]; then
  flutter run -d ios --dart-define "API_BASE_URL=$API_BASE_URL"
else
  echo "[ERROR] Invalid platform: $PLATFORM" >&2
  exit 1
fi
