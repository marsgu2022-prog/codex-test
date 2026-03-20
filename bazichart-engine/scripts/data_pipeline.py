"""
八字数据清洗 + 排盘管线

功能：
1. 读取三个数据源（astrodatabank, astrotheme, wikipedia/wikidata）
2. 统一转换为标准格式
3. 去重（同名+同出生日期）
4. 排盘计算
5. 输出统计报告
"""

import json
import uuid
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# 添加脚本目录到 path
sys.path.insert(0, str(Path(__file__).parent))
from bazi_calculator import calculate_bazi, STEM_ELEMENT, ELEMENT_EN

DATA_DIR = Path(__file__).parent.parent / 'data'


# ============================================================
# 数据源读取与转换
# ============================================================

def load_astro_data():
    """加载 Astro-Databank 数据"""
    filepath = DATA_DIR / 'famous_people_astro.json'
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    results = []
    for item in raw:
        results.append({
            'id': str(uuid.uuid4()),
            'name_en': item.get('name_en', ''),
            'name_zh': item.get('name_zh'),
            'birth_date': item.get('birth_date'),
            'birth_time': item.get('birth_time'),
            'birth_time_reliability': item.get('birth_time_reliability', 'unknown'),
            'birth_city': item.get('birth_city', ''),
            'birth_country': item.get('birth_country', ''),
            'gender': item.get('gender', ''),
            'occupation': item.get('occupation', []),
            'bio': item.get('bio', ''),
            'notable_events': item.get('notable_events', []),
            'source': 'astrodatabank',
            'source_url': item.get('source_urls', [''])[0] if item.get('source_urls') else '',
            'data_quality_score': item.get('data_quality_score', 0.5),
            'rodden_rating': item.get('rodden_rating'),
        })
    return results


def load_astrotheme_data():
    """加载 Astrotheme 数据"""
    filepath = DATA_DIR / 'famous_people_astrotheme.json'
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    results = []
    for item in raw:
        results.append({
            'id': str(uuid.uuid4()),
            'name_en': item.get('name_en', ''),
            'name_zh': item.get('name_zh'),
            'birth_date': item.get('birth_date'),
            'birth_time': item.get('birth_time'),
            'birth_time_reliability': item.get('birth_time_reliability', 'unknown'),
            'birth_city': item.get('birth_city', ''),
            'birth_country': item.get('birth_country', ''),
            'gender': item.get('gender', ''),
            'occupation': item.get('occupation', []),
            'bio': item.get('bio', ''),
            'notable_events': item.get('notable_events', []),
            'source': 'astrotheme',
            'source_url': item.get('source_urls', [''])[0] if item.get('source_urls') else '',
            'data_quality_score': item.get('data_quality_score', 0.5),
            'rodden_rating': None,
        })
    return results


def load_wikipedia_data():
    """加载 Wikipedia/Wikidata 数据（famous_people.json）"""
    filepath = DATA_DIR / 'famous_people.json'
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    results = []
    for item in raw:
        # 从 source 字段提取 URL
        source_info = item.get('source', {})
        source_url = source_info.get('url', '') if isinstance(source_info, dict) else ''

        # 提取出生时间（birth_hour 字段）
        birth_time = None
        if item.get('has_birth_hour') and item.get('birth_hour'):
            bh = item['birth_hour']
            if isinstance(bh, str) and ':' in bh:
                birth_time = bh
            elif isinstance(bh, (int, float)):
                birth_time = f"{int(bh):02d}:00"

        # 确定时辰可靠性
        reliability = 'unknown'
        if birth_time:
            reliability = 'low'  # Wikipedia 来源的时辰可靠性较低

        # 国家
        country = item.get('nationality_en', '')

        # 职业：合并多个职业字段
        occupation = item.get('occupation', [])
        if isinstance(occupation, str):
            occupation = [occupation]

        # bio
        bio = item.get('bio_en') or item.get('summary') or ''

        results.append({
            'id': item.get('id', str(uuid.uuid4())),
            'name_en': item.get('name_en', ''),
            'name_zh': item.get('name_zh') or item.get('name_zh_hans'),
            'birth_date': item.get('birth_date'),
            'birth_time': birth_time,
            'birth_time_reliability': reliability,
            'birth_city': '',
            'birth_country': country,
            'gender': item.get('gender', ''),
            'occupation': occupation,
            'bio': bio,
            'notable_events': [],
            'source': 'wikipedia',
            'source_url': source_url,
            'data_quality_score': 0.3 if not birth_time else 0.5,
            'rodden_rating': None,
            # 保留原始排盘数据用于交叉验证
            '_original_pillars': item.get('pillars'),
            '_original_day_master': item.get('day_master'),
        })
    return results


# ============================================================
# 去重
# ============================================================

def deduplicate(records):
    """
    去重：同名（英文名忽略大小写）+ 同出生日期视为重复。
    优先保留 data_quality_score 更高的记录。
    """
    seen = {}
    duplicates = 0

    # 按质量分降序排，确保高质量的先入 seen
    records.sort(key=lambda x: x.get('data_quality_score', 0), reverse=True)

    unique = []
    for r in records:
        name = (r.get('name_en') or '').strip().lower()
        date = r.get('birth_date', '')
        key = f"{name}|{date}"

        if key in seen:
            duplicates += 1
            # 如果现有记录没有时辰但新记录有，合并时辰信息
            existing = seen[key]
            if not existing.get('birth_time') and r.get('birth_time'):
                existing['birth_time'] = r['birth_time']
                existing['birth_time_reliability'] = r.get('birth_time_reliability', 'low')
            continue

        seen[key] = r
        unique.append(r)

    print(f"去重：发现 {duplicates} 条重复记录")
    return unique


# ============================================================
# 数据验证
# ============================================================

def validate_date(date_str):
    """验证日期格式和范围"""
    if not date_str:
        return False
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return 1900 <= dt.year <= 2100
    except ValueError:
        return False


def validate_time(time_str):
    """验证时间格式"""
    if not time_str:
        return False
    try:
        parts = time_str.split(':')
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return 0 <= h <= 23 and 0 <= m <= 59
    except (ValueError, IndexError):
        return False


# ============================================================
# 排盘处理
# ============================================================

def run_bazi_calculation(records, test_mode=False):
    """对记录列表执行排盘"""
    limit = 10 if test_mode else len(records)
    success = 0
    failed = 0
    skipped = 0
    results = []

    for i, r in enumerate(records[:limit]):
        if not validate_date(r.get('birth_date')):
            r['bazi'] = None
            r['bazi_error'] = 'invalid_date'
            skipped += 1
            results.append(r)
            continue

        try:
            birth_time = r.get('birth_time')
            if birth_time and not validate_time(birth_time):
                birth_time = None

            bazi = calculate_bazi(r['birth_date'], birth_time)

            # 如果有原始排盘数据，做交叉验证
            orig = r.get('_original_pillars')
            if orig and orig.get('day'):
                if bazi['day_pillar'] != orig['day']:
                    print(f"⚠️ 日柱不一致: {r['name_en']} "
                          f"计算={bazi['day_pillar']} 原始={orig['day']}")

            r['bazi'] = bazi
            r['bazi_error'] = None
            success += 1
        except Exception as e:
            r['bazi'] = None
            r['bazi_error'] = str(e)
            failed += 1

        results.append(r)

        if (i + 1) % 1000 == 0:
            print(f"  进度: {i+1}/{limit}")

    print(f"排盘完成: 成功={success}, 失败={failed}, 跳过={skipped}")
    return results


# ============================================================
# 统计报告
# ============================================================

def generate_report(records):
    """生成统计报告"""
    total = len(records)
    has_time = sum(1 for r in records if r.get('birth_time') and validate_time(r.get('birth_time', '')))
    has_bazi = sum(1 for r in records if r.get('bazi'))
    bazi_with_time = sum(1 for r in records if r.get('bazi') and r['bazi'].get('has_birth_time'))

    # 五行分布
    element_totals = Counter()
    for r in records:
        if r.get('bazi') and r['bazi'].get('five_elements_count'):
            for elem, count in r['bazi']['five_elements_count'].items():
                element_totals[elem] += count

    # 日主分布
    day_master_dist = Counter()
    day_master_element_dist = Counter()
    for r in records:
        if r.get('bazi'):
            dm = r['bazi'].get('day_master')
            if dm:
                day_master_dist[dm] += 1
                day_master_element_dist[ELEMENT_EN[STEM_ELEMENT[dm]]] += 1

    # 日主强弱
    strength_dist = Counter()
    for r in records:
        if r.get('bazi') and r['bazi'].get('day_master_strength'):
            strength_dist[r['bazi']['day_master_strength']] += 1

    # 职业分布（Top 20）
    occupation_dist = Counter()
    for r in records:
        for occ in r.get('occupation', []):
            occupation_dist[occ] += 1

    # 数据源分布
    source_dist = Counter()
    for r in records:
        source_dist[r.get('source', 'unknown')] += 1

    report = {
        'summary': {
            'total_records': total,
            'has_birth_time': has_time,
            'bazi_calculated': has_bazi,
            'bazi_with_birth_time': bazi_with_time,
        },
        'source_distribution': dict(source_dist.most_common()),
        'five_elements_total': dict(element_totals.most_common()),
        'day_master_distribution': dict(day_master_dist.most_common()),
        'day_master_element_distribution': dict(day_master_element_dist.most_common()),
        'day_master_strength': dict(strength_dist.most_common()),
        'top_occupations': dict(occupation_dist.most_common(20)),
    }

    return report


def print_report(report):
    """打印统计报告"""
    s = report['summary']
    print("\n" + "=" * 60)
    print("八字数据管线统计报告")
    print("=" * 60)

    print(f"\n📊 总览:")
    print(f"  总条数:         {s['total_records']:,}")
    print(f"  有时辰:         {s['has_birth_time']:,}")
    print(f"  排盘成功:       {s['bazi_calculated']:,}")
    print(f"  有时辰且排盘成功: {s['bazi_with_birth_time']:,}")

    print(f"\n📦 数据源分布:")
    for source, count in report['source_distribution'].items():
        print(f"  {source:20s} {count:,}")

    print(f"\n🔥 五行总计分布:")
    for elem, count in report['five_elements_total'].items():
        bar = '█' * (count // max(1, max(report['five_elements_total'].values()) // 30))
        print(f"  {elem:8s} {count:6,} {bar}")

    print(f"\n☯️ 日主分布（天干）:")
    for dm, count in report['day_master_distribution'].items():
        element = ELEMENT_EN[STEM_ELEMENT[dm]]
        print(f"  {dm} ({element:5s}) {count:,}")

    print(f"\n🌊 日主五行分布:")
    for elem, count in report['day_master_element_distribution'].items():
        print(f"  {elem:8s} {count:,}")

    print(f"\n💪 日主强弱:")
    for strength, count in report['day_master_strength'].items():
        print(f"  {strength:8s} {count:,}")

    print(f"\n👤 职业分布 (Top 20):")
    for occ, count in report['top_occupations'].items():
        print(f"  {occ:20s} {count:,}")


# ============================================================
# 主流程
# ============================================================

def clean_for_output(record):
    """清理内部字段，输出干净的记录"""
    r = dict(record)
    # 移除内部字段
    r.pop('_original_pillars', None)
    r.pop('_original_day_master', None)
    r.pop('bazi_error', None)
    r.pop('rodden_rating', None)
    return r


def main():
    import argparse
    parser = argparse.ArgumentParser(description='八字数据清洗+排盘管线')
    parser.add_argument('--test', action='store_true', help='测试模式：只处理前10条')
    parser.add_argument('--skip-wikipedia', action='store_true', help='跳过 Wikipedia 大数据集')
    parser.add_argument('--step', choices=['clean', 'bazi', 'all'], default='all',
                        help='执行步骤: clean=仅清洗, bazi=仅排盘, all=全部')
    args = parser.parse_args()

    print("=" * 60)
    print("八字数据清洗 + 排盘管线")
    print("=" * 60)

    # Step 1: 加载数据
    print("\n📥 加载数据源...")
    astro_data = load_astro_data()
    print(f"  Astrodatabank: {len(astro_data)} 条")

    astrotheme_data = load_astrotheme_data()
    print(f"  Astrotheme:    {len(astrotheme_data)} 条")

    if args.skip_wikipedia:
        wiki_data = []
        print(f"  Wikipedia:     跳过")
    else:
        wiki_data = load_wikipedia_data()
        print(f"  Wikipedia:     {len(wiki_data)} 条")

    # Step 2: 合并 + 去重
    print("\n🔄 合并去重...")
    all_data = astro_data + astrotheme_data + wiki_data
    print(f"  合并前: {len(all_data)} 条")
    unified = deduplicate(all_data)
    print(f"  合并后: {len(unified)} 条")

    # Step 3: 输出统一数据
    if args.step in ('clean', 'all'):
        output_path = DATA_DIR / 'unified_people.json'
        clean_records = [clean_for_output(r) for r in unified]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clean_records, f, ensure_ascii=False, indent=2)
        print(f"\n💾 统一数据已保存: {output_path} ({len(clean_records)} 条)")

    # Step 4: 排盘
    if args.step in ('bazi', 'all'):
        print("\n🧮 开始排盘计算...")

        # 先跑测试
        if args.test:
            print("  [测试模式] 只处理前10条有时辰的记录")
            has_time_records = [r for r in unified if r.get('birth_time') and validate_time(r['birth_time'])]
            test_records = has_time_records[:10]
            results = run_bazi_calculation(test_records, test_mode=True)

            # 打印测试结果
            print("\n📋 测试结果:")
            for r in results:
                bazi = r.get('bazi')
                if bazi:
                    print(f"  {r['name_en']:30s} {r['birth_date']} {r.get('birth_time','')} → "
                          f"{bazi['year_pillar']} {bazi['month_pillar']} {bazi['day_pillar']} {bazi.get('hour_pillar','?')}")
                else:
                    print(f"  {r['name_en']:30s} ❌ {r.get('bazi_error','unknown')}")
        else:
            # 全量排盘
            print(f"  处理 {len(unified)} 条记录...")
            results = run_bazi_calculation(unified)

            # 交叉验证统计
            cross_check = 0
            cross_match = 0
            for r in results:
                orig = r.get('_original_pillars')
                bazi = r.get('bazi')
                if orig and orig.get('day') and bazi:
                    cross_check += 1
                    if bazi['day_pillar'] == orig['day']:
                        cross_match += 1

            if cross_check > 0:
                pct = cross_match / cross_check * 100
                print(f"\n🔍 交叉验证: {cross_match}/{cross_check} 匹配 ({pct:.1f}%)")

            # 输出带排盘的数据
            output_path = DATA_DIR / 'unified_people_with_bazi.json'
            clean_results = [clean_for_output(r) for r in results]
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(clean_results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 排盘数据已保存: {output_path}")

            # 生成报告
            report = generate_report(results)
            print_report(report)

            # 保存报告 JSON
            report_path = DATA_DIR / 'pipeline_report.json'
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n📊 报告已保存: {report_path}")


if __name__ == '__main__':
    main()
