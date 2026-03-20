#!/bin/bash
# 八字全管线一键运行脚本
# 用法：
#   ./scripts/run_full_pipeline.sh          # 全量
#   ./scripts/run_full_pipeline.sh --dry-run  # 不调DeepSeek API
#   ./scripts/run_full_pipeline.sh --test   # 各步骤只跑少量数据

set -e  # 任意步骤失败即退出

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."  # 切到 bazichart-engine 根目录

DRY_RUN=""
TEST_MODE=""
READER_ARGS=""

for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN="1"
      READER_ARGS="--dry-run"
      ;;
    --test)
      TEST_MODE="1"
      READER_ARGS="--limit 10"
      ;;
  esac
done

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        八字全管线 BaZi Pipeline      ║"
echo "╚══════════════════════════════════════╝"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  目录: $(pwd)"
[ -n "$DRY_RUN" ]  && echo "  模式: Dry-run（不调API）"
[ -n "$TEST_MODE" ] && echo "  模式: 测试（限制条数）"
echo ""

# ── Step 1: 数据清洗 + 统一格式 ────────────────────────────
echo "▶ Step 1: 数据清洗 + 排盘"
echo "─────────────────────────────────────"
if [ -n "$TEST_MODE" ]; then
  python3 scripts/data_pipeline.py --skip-wikipedia
else
  python3 scripts/data_pipeline.py
fi
echo ""

# ── Step 2: 特征提取 ────────────────────────────────────────
echo "▶ Step 2: 特征提取"
echo "─────────────────────────────────────"
if [ -n "$TEST_MODE" ]; then
  python3 scripts/feature_extractor.py --test
else
  python3 scripts/feature_extractor.py
fi
echo ""

# ── Step 3: 自动研读 ────────────────────────────────────────
echo "▶ Step 3: 自动研读（有时辰数据）"
echo "─────────────────────────────────────"

if [ -z "$DRY_RUN" ] && [ -z "$DEEPSEEK_API_KEY" ]; then
  echo "⚠️  警告：DEEPSEEK_API_KEY 未设置，跳过研读步骤"
  echo "   运行前请: export DEEPSEEK_API_KEY=sk-..."
else
  python3 scripts/auto_reader.py $READER_ARGS
fi
echo ""

# ── Step 4: 质量检查 ────────────────────────────────────────
echo "▶ Step 4: 研读质量检查"
echo "─────────────────────────────────────"
READINGS_FILE="data/bazi_readings.json"

if [ -f "$READINGS_FILE" ]; then
  python3 scripts/reading_validator.py
else
  echo "⚠️  找不到 $READINGS_FILE，跳过质量检查"
  echo "   请先运行 Step 3 生成研读数据"
fi
echo ""

# ── 完成 ────────────────────────────────────────────────────
echo "╔══════════════════════════════════════╗"
echo "║              管线完成                ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "输出文件："
for f in \
  data/unified_people.json \
  data/unified_people_with_bazi.json \
  data/training_features.json \
  data/feature_vectors.csv \
  data/feature_stats.json \
  data/bazi_readings.json \
  data/reading_quality_report.json
do
  if [ -f "$f" ]; then
    size=$(du -sh "$f" 2>/dev/null | cut -f1)
    lines=$(python3 -c "import json; d=json.load(open('$f')); print(len(d))" 2>/dev/null || echo "?")
    echo "  ✅ $f  ($size, $lines 条)"
  else
    echo "  ⬜ $f  (未生成)"
  fi
done
echo ""
echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
