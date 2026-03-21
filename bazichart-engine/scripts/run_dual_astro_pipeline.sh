#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

if [ -x "/opt/homebrew/bin/python3" ]; then
  PYTHON_BIN="/opt/homebrew/bin/python3"
elif [ -x "/usr/local/bin/python3" ]; then
  PYTHON_BIN="/usr/local/bin/python3"
else
  PYTHON_BIN="$(command -v python3)"
fi

DATA_DIR="bazichart-engine/data"
ASTRO_A="$DATA_DIR/famous_people_astro.json"
ASTRO_B="$DATA_DIR/famous_people_astro_b.json"
ASTRO_ERRORS="$DATA_DIR/crawl_errors.json"
ASTRO_STATE="$DATA_DIR/astro_crawl_state.json"
ASTROTHEME_DATA="$DATA_DIR/famous_people_astrotheme.json"
ASTROTHEME_ERRORS="$DATA_DIR/crawl_errors_astrotheme.json"
ASTROTHEME_STATE="$DATA_DIR/astrotheme_crawl_state.json"
PIPELINE_REPORT="$DATA_DIR/pipeline_report.json"
UNIFIED="$DATA_DIR/unified_people.json"
UNIFIED_BAZI="$DATA_DIR/unified_people_with_bazi.json"
LOG_FILE="$DATA_DIR/dual_astro_pipeline.log"

TARGET_HAS_TIME="${1:-10000}"
ASTRO_BATCH_SIZE="${2:-200}"
ASTROTHEME_BATCH_SIZE="${3:-300}"
ASTRO_MAX_PAGES="${4:-500}"
ASTROTHEME_MAX_PAGES="${5:-15}"

count_json_list() {
  "$PYTHON_BIN" - "$1" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.exists():
    print(0)
else:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    print(len(payload) if isinstance(payload, list) else 0)
PY
}

count_has_time() {
  "$PYTHON_BIN" - "$PIPELINE_REPORT" "$UNIFIED" <<'PY'
import json, sys
from pathlib import Path
report_path = Path(sys.argv[1])
unified_path = Path(sys.argv[2])
if report_path.exists():
    with report_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    print(payload.get("summary", {}).get("has_birth_time", 0))
elif unified_path.exists():
    with unified_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    count = 0
    for item in payload:
        if item.get("birth_time"):
            count += 1
    print(count)
else:
    print(0)
PY
}

idle_rounds=0

echo "$(date '+%F %T') 双源批跑启动，目标有时辰=${TARGET_HAS_TIME}" | tee -a "$LOG_FILE"
echo "$(date '+%F %T') 使用Python=${PYTHON_BIN}" | tee -a "$LOG_FILE"

while true; do
  current_has_time="$(count_has_time)"
  if [ "$current_has_time" -ge "$TARGET_HAS_TIME" ]; then
    echo "$(date '+%F %T') 已达到目标，有时辰=${current_has_time}" | tee -a "$LOG_FILE"
    exit 0
  fi

  before_astro="$(count_json_list "$ASTRO_A")"
  before_theme="$(count_json_list "$ASTROTHEME_DATA")"

  echo "$(date '+%F %T') 开始批次：AA/A=${before_astro} Astrotheme=${before_theme} 有时辰=${current_has_time}" | tee -a "$LOG_FILE"

  "$PYTHON_BIN" bazichart-engine/scripts/crawl_astro_databank.py \
    --max-pages "$ASTRO_MAX_PAGES" \
    --max-records "$ASTRO_BATCH_SIZE" | tee -a "$LOG_FILE"

  "$PYTHON_BIN" bazichart-engine/scripts/crawl_astrotheme.py \
    --max-pages-per-category "$ASTROTHEME_MAX_PAGES" \
    --max-records "$ASTROTHEME_BATCH_SIZE" \
    --state-output "$ASTROTHEME_STATE" | tee -a "$LOG_FILE"

  "$PYTHON_BIN" bazichart-engine/scripts/data_pipeline.py | tee -a "$LOG_FILE"

  after_astro="$(count_json_list "$ASTRO_A")"
  after_theme="$(count_json_list "$ASTROTHEME_DATA")"
  after_has_time="$(count_has_time)"
  added_astro=$((after_astro - before_astro))
  added_theme=$((after_theme - before_theme))

  git add \
    "$ASTRO_A" \
    "$ASTRO_B" \
    "$ASTRO_ERRORS" \
    "$ASTRO_STATE" \
    "$ASTROTHEME_DATA" \
    "$ASTROTHEME_ERRORS" \
    "$ASTROTHEME_STATE" \
    "$PIPELINE_REPORT" \
    "$UNIFIED" \
    "$UNIFIED_BAZI"

  if ! git diff --cached --quiet; then
    git commit -m "双源抓取：AA/A ${after_astro} 条 Astrotheme ${after_theme} 条 有时辰 ${after_has_time} 条" | tee -a "$LOG_FILE"
    GIT_TERMINAL_PROMPT=0 git push origin main | tee -a "$LOG_FILE"
  fi

  echo "$(date '+%F %T') 批次完成：AA/A新增=${added_astro} Astrotheme新增=${added_theme} 有时辰=${after_has_time}" | tee -a "$LOG_FILE"

  if [ "$added_astro" -le 0 ] && [ "$added_theme" -le 0 ]; then
    idle_rounds=$((idle_rounds + 1))
    if [ "$idle_rounds" -ge 3 ]; then
      echo "$(date '+%F %T') 连续3轮无新增，停止批跑" | tee -a "$LOG_FILE"
      exit 0
    fi
    sleep 300
  else
    idle_rounds=0
  fi
done
