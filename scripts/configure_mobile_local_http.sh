#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT_DIR/mobile/flutter/app"
ANDROID_MANIFEST="$APP_DIR/android/app/src/main/AndroidManifest.xml"
IOS_PLIST="$APP_DIR/ios/Runner/Info.plist"

if [[ -f "$ANDROID_MANIFEST" ]]; then
  if ! grep -q 'android:usesCleartextTraffic=' "$ANDROID_MANIFEST"; then
    perl -0777 -i -pe 's#<application([^>]*)>#<application$1 android:usesCleartextTraffic="true">#s' "$ANDROID_MANIFEST"
    echo "[INFO] Android cleartextTraffic enabled"
  else
    echo "[INFO] Android cleartextTraffic already configured"
  fi
else
  echo "[WARN] AndroidManifest not found: $ANDROID_MANIFEST"
fi

if [[ -f "$IOS_PLIST" ]]; then
  if command -v /usr/libexec/PlistBuddy >/dev/null 2>&1; then
    /usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity dict" "$IOS_PLIST" 2>/dev/null || true
    /usr/libexec/PlistBuddy -c "Set :NSAppTransportSecurity:NSAllowsArbitraryLoads true" "$IOS_PLIST" 2>/dev/null || \
      /usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity:NSAllowsArbitraryLoads bool true" "$IOS_PLIST"
    /usr/libexec/PlistBuddy -c "Set :NSAppTransportSecurity:NSAllowsLocalNetworking true" "$IOS_PLIST" 2>/dev/null || \
      /usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity:NSAllowsLocalNetworking bool true" "$IOS_PLIST"
    echo "[INFO] iOS ATS relaxed for local dev"
  else
    echo "[WARN] PlistBuddy not available, skip iOS ATS patch"
  fi
else
  echo "[WARN] Info.plist not found: $IOS_PLIST"
fi

echo "[DONE] Local HTTP config applied (dev only)"
