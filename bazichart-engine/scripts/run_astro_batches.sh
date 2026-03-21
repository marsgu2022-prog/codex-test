#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

DATA_A="bazichart-engine/data/famous_people_astro.json"
DATA_B="bazichart-engine/data/famous_people_astro_b.json"
ERRORS="bazichart-engine/data/crawl_errors.json"
STATE="bazichart-engine/data/astro_crawl_state.json"
CRAWLER="bazichart-engine/scripts/crawl_astro_databank.py"
LOG_FILE="bazichart-engine/data/astro_batch_runner.log"
TARGET_TOTAL="${1:-5000}"
BATCH_SIZE="${2:-200}"

count_json_list() {
  python3 - "$1" <<'PY'
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

while true; do
  before_count="$(count_json_list "$DATA_A")"
  if [ "$before_count" -ge "$TARGET_TOTAL" ]; then
    echo "$(date '+%F %T') 已达到目标：$before_count" | tee -a "$LOG_FILE"
    exit 0
  fi

  echo "$(date '+%F %T') 开始抓取批次，当前 AA/A: $before_count" | tee -a "$LOG_FILE"
  python3 "$CRAWLER" --max-pages 500 --max-records "$BATCH_SIZE" | tee -a "$LOG_FILE"

  after_count="$(count_json_list "$DATA_A")"
  added_count=$((after_count - before_count))

  if [ "$added_count" -le 0 ]; then
    echo "$(date '+%F %T') 本轮未新增数据，等待5分钟后重试" | tee -a "$LOG_FILE"
    sleep 300
    continue
  fi

  git add "$CRAWLER" "$DATA_A" "$DATA_B" "$ERRORS" "$STATE"
  git commit -m "Astro-Databank扩充至${after_count}条AA/A" | tee -a "$LOG_FILE"
  GIT_TERMINAL_PROMPT=0 git push origin main | tee -a "$LOG_FILE"

  echo "✅ Astro批次完成，新增${added_count}条，当前总计${after_count}条AA/A" | tee -a "$LOG_FILE"
done
