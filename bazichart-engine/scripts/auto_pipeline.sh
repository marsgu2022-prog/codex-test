#!/bin/bash
# auto_pipeline.sh — 每天凌晨3点跑数据管线，生成 pipeline_report.json
# Cron: 0 3 * * *
# Log:  /opt/bazichart-engine/logs/auto_pipeline.log

BASE=/opt/bazichart-engine
BAZI=$BASE/bazichart-engine
LOG=$BASE/logs/auto_pipeline.log

ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] ===== data_pipeline 开始 =====" >> "$LOG"

cd "$BAZI" || { echo "[$(ts)] ERROR: cd $BAZI 失败" >> "$LOG"; exit 1; }

# 加载环境变量（DEEPSEEK_API_KEY 等）
set -a; source .env 2>/dev/null; set +a

python3 "$BAZI/scripts/data_pipeline.py" >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(ts)] data_pipeline 结束，exit=$EXIT_CODE" >> "$LOG"

# 确认报告文件已生成
if [ -f "$BAZI/data/pipeline_report.json" ]; then
    SIZE=$(wc -c < "$BAZI/data/pipeline_report.json")
    echo "[$(ts)] pipeline_report.json 已生成，大小=${SIZE}B" >> "$LOG"
else
    echo "[$(ts)] WARN: pipeline_report.json 未找到" >> "$LOG"
fi

tail -1000 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
