#!/usr/bin/env bash
set -euo pipefail

LABEL="com.codex.dual-astro-pipeline"
LOG_PATH="$(cd "$(dirname "$0")/../.." && pwd)/bazichart-engine/data/dual_astro_pipeline.log"

echo "== launchctl =="
launchctl print "gui/$(id -u)/$LABEL" | sed -n '1,80p' || true
echo
echo "== log tail =="
sed -n '1,120p' "$LOG_PATH" | tail -n 40 || true
