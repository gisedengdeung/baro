#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT_DIR/mobile/flutter/app"

if ! command -v flutter >/dev/null 2>&1; then
  echo "[ERROR] flutter not found. Install Flutter SDK first." >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/pubspec.yaml" ]]; then
  echo "[ERROR] Flutter app not found at $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

if [[ ! -d "android" || ! -d "ios" ]]; then
  echo "[INFO] Generating platform folders (android, ios)"
  flutter create . --platforms=android,ios
fi

flutter pub get

"$ROOT_DIR/scripts/configure_mobile_local_http.sh"

echo "[DONE] Mobile setup completed"
echo "Next: ./scripts/run_mobile.sh --platform android --api-base-url http://10.0.2.2:8000"
