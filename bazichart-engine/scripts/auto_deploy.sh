#!/bin/bash
# auto_deploy.sh — 每小时检查 git 更新，有新 commit 才重启服务
# Cron: 0 * * * *
# Log:  /opt/bazichart-engine/logs/auto_deploy.log

BASE=/opt/bazichart-engine
LOG=$BASE/logs/auto_deploy.log

ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] 开始检查更新" >> "$LOG"

cd "$BASE" || { echo "[$(ts)] ERROR: cd $BASE 失败" >> "$LOG"; exit 1; }

git fetch origin main >> "$LOG" 2>&1

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "[$(ts)] 无更新 (${LOCAL:0:8})" >> "$LOG"
else
    echo "[$(ts)] 发现更新 ${LOCAL:0:8} -> ${REMOTE:0:8}，开始 pull" >> "$LOG"
    git pull >> "$LOG" 2>&1

    echo "[$(ts)] 重启 bazichart 服务" >> "$LOG"
    systemctl restart bazichart >> "$LOG" 2>&1
    sleep 3
    STATUS=$(systemctl is-active bazichart)
    echo "[$(ts)] 服务状态: $STATUS" >> "$LOG"
fi

# 日志滚动，保留最近 1000 行
tail -1000 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
