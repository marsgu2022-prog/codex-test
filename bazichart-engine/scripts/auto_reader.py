"""
八字自动研读脚本 — Auto BaZi Reading via DeepSeek API

功能：
- 筛选有完整时辰的记录（birth_time_reliability != unknown）
- 构建命理分析 prompt，调用 DeepSeek API
- 解析返回 JSON，合并到原数据
- 限速：每秒最多2次请求，失败重试1次

用法：
  python3 scripts/auto_reader.py              # 全量运行
  python3 scripts/auto_reader.py --dry-run    # 打印prompt不调API
  python3 scripts/auto_reader.py --limit 10  # 只跑前10条
  python3 scripts/auto_reader.py --limit 10 --dry-run
"""

import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

DATA_DIR    = Path(__file__).parent.parent / 'data'
PROMPTS_DIR = Path(__file__).parent.parent / 'prompts'


# ============================================================
# Prompt 构建
# ============================================================

def load_prompt_template():
    with open(PROMPTS_DIR / 'reading_prompt.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def build_prompt(record, template):
    """构建单条记录的 prompt"""
    bazi = record['bazi']
    hour_pillar = bazi.get('hour_pillar') or '（无时辰）'

    user_msg = template['user_prompt_template'].format(
        name       = record.get('name_en') or record.get('name_zh') or '未知',
        year_pillar  = bazi['year_pillar'],
        month_pillar = bazi['month_pillar'],
        day_pillar   = bazi['day_pillar'],
        hour_pillar  = hour_pillar,
        gender     = record.get('gender') or '未知',
        occupation = '、'.join(record.get('occupation') or []) or '未知',
        bio        = (record.get('bio') or '')[:300],  # 截断避免token超限
        output_schema = json.dumps(template['output_schema'], ensure_ascii=False, indent=2),
    )
    return template['system_prompt'], user_msg


# ============================================================
# DeepSeek API 调用
# ============================================================

def call_deepseek(system_prompt, user_prompt, api_key, timeout=30):
    """
    调用 DeepSeek Chat API。
    返回 (response_text, error_message)
    """
    url = 'https://api.deepseek.com/v1/chat/completions'
    payload = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user',   'content': user_prompt},
        ],
        'temperature': 0.3,      # 命理分析要稳定
        'max_tokens': 1500,
        'response_format': {'type': 'json_object'},  # 强制JSON输出
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Content-Type':  'application/json',
            'Authorization': f'Bearer {api_key}',
            'Accept':        'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode('utf-8'))
            content = body['choices'][0]['message']['content']
            return content, None
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return None, f'HTTP {e.code}: {body[:200]}'
    except urllib.error.URLError as e:
        return None, f'URLError: {e.reason}'
    except Exception as e:
        return None, f'{type(e).__name__}: {e}'


def parse_reading(raw_text, record_id):
    """
    解析 DeepSeek 返回的 JSON 字符串。
    返回 (parsed_dict, error_message)
    """
    if not raw_text:
        return None, 'empty response'

    # 去除可能的 Markdown 包裹
    text = raw_text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1]) if lines[-1].strip() == '```' else '\n'.join(lines[1:])

    try:
        parsed = json.loads(text)
        return parsed, None
    except json.JSONDecodeError as e:
        return None, f'JSON parse error: {e} | raw: {text[:200]}'


# ============================================================
# 限速器
# ============================================================

class RateLimiter:
    """简单令牌桶限速：每秒最多 max_rps 次"""
    def __init__(self, max_rps=2):
        self.interval = 1.0 / max_rps
        self.last_call = 0.0

    def wait(self):
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_call = time.time()


# ============================================================
# 主流程
# ============================================================

def filter_records(data):
    """筛选有完整时辰且排盘成功的记录"""
    valid = []
    for r in data:
        bazi = r.get('bazi')
        if not bazi:
            continue
        if not bazi.get('has_birth_time'):
            continue
        if not bazi.get('hour_pillar'):
            continue
        valid.append(r)
    return valid


def main():
    parser = argparse.ArgumentParser(description='八字自动研读')
    parser.add_argument('--dry-run', action='store_true',
                        help='打印prompt但不调API')
    parser.add_argument('--limit', type=int, default=0,
                        help='限制处理条数（0=全量）')
    parser.add_argument('--resume', action='store_true',
                        help='跳过已有结果的记录（断点续跑）')
    args = parser.parse_args()

    print("=" * 60)
    print("八字自动研读")
    print("=" * 60)

    # 读取数据
    input_path = DATA_DIR / 'unified_people_with_bazi.json'
    with open(input_path, 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    records = filter_records(all_data)
    print(f"\n有完整时辰的记录: {len(records)} 条")

    if args.limit > 0:
        records = records[:args.limit]
        print(f"[限制模式] 只处理前 {len(records)} 条")

    # 加载 prompt 模板
    template = load_prompt_template()

    # 断点续跑：加载已有结果
    readings_path = DATA_DIR / 'bazi_readings.json'
    errors_path   = DATA_DIR / 'reading_errors.json'

    existing_readings = {}
    if args.resume and readings_path.exists():
        with open(readings_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        existing_readings = {r['id']: r for r in existing}
        print(f"[续跑] 已有 {len(existing_readings)} 条结果")

    # Dry-run 模式
    if args.dry_run:
        print(f"\n[Dry-run] 打印前 {min(3, len(records))} 条 prompt\n")
        for r in records[:3]:
            sys_p, usr_p = build_prompt(r, template)
            print(f"{'='*50}")
            print(f"ID: {r['id']}")
            print(f"人物: {r['name_en']} ({r['birth_date']})")
            print(f"四柱: {r['bazi']['year_pillar']} {r['bazi']['month_pillar']} "
                  f"{r['bazi']['day_pillar']} {r['bazi']['hour_pillar']}")
            print(f"\n--- System Prompt ---")
            print(sys_p)
            print(f"\n--- User Prompt (前500字) ---")
            print(usr_p[:500], '...')
            print()
        print(f"[Dry-run] 完成。共 {len(records)} 条待处理，向量维度无误。")
        return

    # 检查 API key
    api_key = os.environ.get('DEEPSEEK_API_KEY', '').strip()
    if not api_key:
        print("\n❌ 错误：未设置环境变量 DEEPSEEK_API_KEY")
        print("   export DEEPSEEK_API_KEY=sk-...")
        sys.exit(1)

    # 开始处理
    rate_limiter = RateLimiter(max_rps=2)
    readings = list(existing_readings.values())
    errors   = []

    success_count = len(existing_readings)
    fail_count    = 0
    skip_count    = 0

    print(f"\n🚀 开始研读 {len(records)} 条记录...")
    print(f"   限速: 2次/秒  超时: 30秒  重试: 1次\n")

    start_time = time.time()

    for i, record in enumerate(records):
        rid = record['id']

        # 断点续跑：跳过已有
        if args.resume and rid in existing_readings:
            skip_count += 1
            continue

        sys_p, usr_p = build_prompt(record, template)

        # 调用 API（含一次重试）
        reading = None
        last_error = None

        for attempt in range(2):
            rate_limiter.wait()
            raw, err = call_deepseek(sys_p, usr_p, api_key)

            if err:
                last_error = err
                if attempt == 0:
                    print(f"  [{i+1}/{len(records)}] ⚠️ 重试 {record['name_en']}: {err[:80]}")
                    time.sleep(2)
                continue

            parsed, parse_err = parse_reading(raw, rid)
            if parse_err:
                last_error = parse_err
                if attempt == 0:
                    print(f"  [{i+1}/{len(records)}] ⚠️ JSON解析重试 {record['name_en']}: {parse_err[:80]}")
                    time.sleep(1)
                continue

            reading = parsed
            break

        if reading:
            result = {
                'id':           rid,
                'name_en':      record.get('name_en'),
                'birth_date':   record.get('birth_date'),
                'bazi_pillars': {
                    'year':  record['bazi']['year_pillar'],
                    'month': record['bazi']['month_pillar'],
                    'day':   record['bazi']['day_pillar'],
                    'hour':  record['bazi']['hour_pillar'],
                },
                'source':    record.get('source'),
                'reading':   reading,
                'read_at':   datetime.utcnow().isoformat() + 'Z',
            }
            readings.append(result)
            success_count += 1

            dm = reading.get('day_master', '?')
            pat = reading.get('pattern', '?')
            conf = reading.get('confidence', 0)
            print(f"  [{i+1}/{len(records)}] ✅ {record['name_en']:30s} "
                  f"日主:{dm} 格局:{pat} 置信:{conf}")
        else:
            errors.append({
                'id':       rid,
                'name_en':  record.get('name_en'),
                'error':    last_error,
                'fail_at':  datetime.utcnow().isoformat() + 'Z',
            })
            fail_count += 1
            print(f"  [{i+1}/{len(records)}] ❌ {record['name_en']:30s} {last_error[:80]}")

        # 每20条保存一次中间结果
        if (i + 1) % 20 == 0:
            _save_json(readings, readings_path)
            _save_json(errors, errors_path)
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (len(records) - i - 1) / rate
            print(f"\n  💾 中间保存: 成功={success_count} 失败={fail_count} "
                  f"剩余~{remaining:.0f}秒\n")

    # 最终保存
    _save_json(readings, readings_path)
    _save_json(errors, errors_path)

    elapsed = time.time() - start_time
    total = success_count + fail_count + skip_count
    print(f"\n{'='*60}")
    print(f"研读完成")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  跳过: {skip_count}")
    print(f"  耗时: {elapsed:.1f}秒")
    if success_count > 0:
        print(f"  成功率: {success_count/(success_count+fail_count)*100:.1f}%")
    print(f"\n💾 {readings_path}")
    print(f"💾 {errors_path}")


def _save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
