#!/bin/bash
# auto_reader_cron.sh — 每天凌晨4点批量研读，每天最多50条，断点续跑
# Cron: 0 4 * * *
# Log:  /opt/bazichart-engine/logs/auto_reader.log

BASE=/opt/bazichart-engine
BAZI=$BASE/bazichart-engine
LOG=$BASE/logs/auto_reader.log

ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] ===== auto_reader 开始（--limit 50 --resume）=====" >> "$LOG"

cd "$BAZI" || { echo "[$(ts)] ERROR: cd $BAZI 失败" >> "$LOG"; exit 1; }

# 加载 DEEPSEEK_API_KEY
set -a; source .env 2>/dev/null; set +a

if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "[$(ts)] ERROR: DEEPSEEK_API_KEY 未设置，退出" >> "$LOG"
    exit 1
fi

python3 "$BAZI/scripts/auto_reader.py" \
    --style qianlong \
    --limit 50 \
    --resume \
    >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(ts)] auto_reader 结束，exit=$EXIT_CODE" >> "$LOG"

# 统计已完成研读数量
if [ -f "$BAZI/data/bazi_readings.json" ]; then
    COUNT=$(python3 -c "import json; print(len(json.load(open('$BAZI/data/bazi_readings.json'))))" 2>/dev/null)
    echo "[$(ts)] bazi_readings.json 当前总条数: ${COUNT:-未知}" >> "$LOG"
fi

tail -2000 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
