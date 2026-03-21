#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PLIST_PATH="$ROOT_DIR/bazichart-engine/data/com.codex.dual-astro-pipeline.plist"
LOG_PATH="$ROOT_DIR/bazichart-engine/data/dual_astro_pipeline.log"
RUNNER_PATH="$ROOT_DIR/bazichart-engine/scripts/run_dual_astro_pipeline.sh"

TARGET_HAS_TIME="${1:-10000}"
ASTRO_BATCH_SIZE="${2:-200}"
ASTROTHEME_BATCH_SIZE="${3:-300}"
ASTRO_MAX_PAGES="${4:-500}"
ASTROTHEME_MAX_PAGES="${5:-15}"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.codex.dual-astro-pipeline</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$RUNNER_PATH</string>
    <string>$TARGET_HAS_TIME</string>
    <string>$ASTRO_BATCH_SIZE</string>
    <string>$ASTROTHEME_BATCH_SIZE</string>
    <string>$ASTRO_MAX_PAGES</string>
    <string>$ASTROTHEME_MAX_PAGES</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StandardOutPath</key>
  <string>$LOG_PATH</string>
  <key>StandardErrorPath</key>
  <string>$LOG_PATH</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/com.codex.dual-astro-pipeline" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/com.codex.dual-astro-pipeline"
echo "plist=$PLIST_PATH"
