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
RUNTIME_DIR="$DATA_DIR/dual_astro_runtime"
GIT_LOCK_DIR="$RUNTIME_DIR/git.lock"
ASTRO_DONE_MARKER="$RUNTIME_DIR/astro.last_done"
ASTROTHEME_DONE_MARKER="$RUNTIME_DIR/astrotheme.last_done"
PIPELINE_DONE_MARKER="$RUNTIME_DIR/pipeline.last_done"

TARGET_HAS_TIME="${1:-10000}"
ASTRO_BATCH_SIZE="${2:-200}"
ASTROTHEME_BATCH_SIZE="${3:-300}"
ASTRO_MAX_PAGES="${4:-500}"
ASTROTHEME_MAX_PAGES="${5:-15}"

mkdir -p "$RUNTIME_DIR"
touch "$ASTRO_DONE_MARKER" "$ASTROTHEME_DONE_MARKER" "$PIPELINE_DONE_MARKER"

log() {
  local message="$1"
  echo "$(date '+%F %T') ${message}" | tee -a "$LOG_FILE"
}

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
    print(sum(1 for item in payload if item.get("birth_time")))
else:
    print(0)
PY
}

acquire_git_lock() {
  while ! mkdir "$GIT_LOCK_DIR" 2>/dev/null; do
    sleep 2
  done
}

release_git_lock() {
  rmdir "$GIT_LOCK_DIR" 2>/dev/null || true
}

git_commit_push_if_needed() {
  local commit_message="$1"
  shift
  acquire_git_lock
  git add "$@"
  if ! git diff --cached --quiet; then
    if git commit -m "$commit_message" | tee -a "$LOG_FILE"; then
      if ! GIT_TERMINAL_PROMPT=0 git push origin main | tee -a "$LOG_FILE"; then
        log "Git push失败，已跳过远端推送并继续抓取"
      fi
    else
      log "Git commit失败，已跳过本批提交并继续抓取"
    fi
  fi
  release_git_lock
}

astro_loop() {
  local idle_rounds=0
  while true; do
    local current_has_time
    current_has_time="$(count_has_time)"
    if [ "$current_has_time" -ge "$TARGET_HAS_TIME" ]; then
      log "Astro-Databank达到目标阈值，停止抓取"
      return 0
    fi

    local before_count after_count added_count
    before_count="$(count_json_list "$ASTRO_A")"
    log "Astro-Databank批次开始：AA/A=${before_count}"

    "$PYTHON_BIN" bazichart-engine/scripts/crawl_astro_databank.py \
      --max-pages "$ASTRO_MAX_PAGES" \
      --max-records "$ASTRO_BATCH_SIZE" | tee -a "$LOG_FILE"

    after_count="$(count_json_list "$ASTRO_A")"
    added_count=$((after_count - before_count))

    if [ "$added_count" -le 0 ]; then
      idle_rounds=$((idle_rounds + 1))
      log "Astro-Databank本轮无新增，连续空轮=${idle_rounds}"
      if [ "$idle_rounds" -ge 3 ]; then
        log "Astro-Databank连续3轮无新增，停止抓取"
        return 0
      fi
      sleep 300
      continue
    fi

    idle_rounds=0
    touch "$ASTRO_DONE_MARKER"
    git_commit_push_if_needed \
      "Astro-Databank扩充至${after_count}条AA/A" \
      "$ASTRO_A" "$ASTRO_B" "$ASTRO_ERRORS" "$ASTRO_STATE"
    log "Astro-Databank批次完成：新增=${added_count} 当前AA/A=${after_count}"
  done
}

astrotheme_loop() {
  local idle_rounds=0
  while true; do
    local current_has_time
    current_has_time="$(count_has_time)"
    if [ "$current_has_time" -ge "$TARGET_HAS_TIME" ]; then
      log "Astrotheme达到目标阈值，停止抓取"
      return 0
    fi

    local before_count after_count added_count
    before_count="$(count_json_list "$ASTROTHEME_DATA")"
    log "Astrotheme批次开始：总数=${before_count}"

    "$PYTHON_BIN" bazichart-engine/scripts/crawl_astrotheme.py \
      --max-pages-per-category "$ASTROTHEME_MAX_PAGES" \
      --max-records "$ASTROTHEME_BATCH_SIZE" \
      --state-output "$ASTROTHEME_STATE" | tee -a "$LOG_FILE"

    after_count="$(count_json_list "$ASTROTHEME_DATA")"
    added_count=$((after_count - before_count))

    if [ "$added_count" -le 0 ]; then
      idle_rounds=$((idle_rounds + 1))
      log "Astrotheme本轮无新增，连续空轮=${idle_rounds}"
      if [ "$idle_rounds" -ge 3 ]; then
        log "Astrotheme连续3轮无新增，停止抓取"
        return 0
      fi
      sleep 300
      continue
    fi

    idle_rounds=0
    touch "$ASTROTHEME_DONE_MARKER"
    git_commit_push_if_needed \
      "Astrotheme扩充至${after_count}条有时辰数据" \
      "$ASTROTHEME_DATA" "$ASTROTHEME_ERRORS" "$ASTROTHEME_STATE"
    log "Astrotheme批次完成：新增=${added_count} 当前总数=${after_count}"
  done
}

pipeline_loop() {
  local last_seen_has_time=0
  while true; do
    local current_has_time
    current_has_time="$(count_has_time)"
    if [ "$current_has_time" -ge "$TARGET_HAS_TIME" ]; then
      log "Pipeline达到目标阈值，停止合并"
      return 0
    fi

    if [ "$ASTRO_DONE_MARKER" -nt "$PIPELINE_DONE_MARKER" ] || [ "$ASTROTHEME_DONE_MARKER" -nt "$PIPELINE_DONE_MARKER" ]; then
      log "Pipeline开始：检测到至少一侧有新数据"
      "$PYTHON_BIN" bazichart-engine/scripts/data_pipeline.py | tee -a "$LOG_FILE"
      touch "$PIPELINE_DONE_MARKER"

      local after_has_time
      after_has_time="$(count_has_time)"
      git_commit_push_if_needed \
        "更新统一人物库：有时辰 ${after_has_time} 条" \
        "$PIPELINE_REPORT" "$UNIFIED" "$UNIFIED_BAZI"
      log "Pipeline完成：有时辰=${after_has_time} 上次=${last_seen_has_time}"
      last_seen_has_time="$after_has_time"
    fi

    sleep 30
  done
}

log "双源批跑启动，目标有时辰=${TARGET_HAS_TIME}"
log "使用Python=${PYTHON_BIN}"

astro_loop &
ASTRO_PID=$!

astrotheme_loop &
ASTROTHEME_PID=$!

pipeline_loop &
PIPELINE_PID=$!

cleanup() {
  kill "$ASTRO_PID" "$ASTROTHEME_PID" "$PIPELINE_PID" >/dev/null 2>&1 || true
  release_git_lock
}

trap cleanup EXIT INT TERM

wait "$ASTRO_PID" "$ASTROTHEME_PID" "$PIPELINE_PID"
