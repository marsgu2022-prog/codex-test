"""
研读质量检查脚本 — Reading Quality Validator

检查 bazi_readings.json：
1. JSON 字段完整性
2. 日主判断与排盘引擎一致性
3. 置信度分布
4. 职业预测与实际职业匹配率
5. 输出质量报告
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path(__file__).parent.parent / 'data'

# 必须存在的字段
REQUIRED_FIELDS = [
    'day_master', 'day_master_strength', 'strength_reasoning',
    'pattern', 'pattern_reasoning', 'useful_god', 'useful_god_reasoning',
    'harmful_god', 'career_tendency', 'career_reasoning',
    'personality_traits', 'life_phases', 'known_events_match', 'confidence',
]

# 职业方向关键词映射（用于粗粒度匹配）
CAREER_KEYWORD_MAP = {
    '作家':    ['写作', '文学', '媒体', '编辑', '记者', '出版', '文字', '内容'],
    '政治家':  ['政治', '仕途', '管理', '领导', '官场', '行政', '公务'],
    '演员':    ['演艺', '表演', '艺术', '娱乐', '影视', '戏剧', '创作'],
    '音乐家':  ['音乐', '艺术', '表演', '创作', '娱乐'],
    '企业家':  ['商业', '创业', '经商', '管理', '实业', '投资', '金融'],
    '科学家':  ['科研', '学术', '技术', '研究', '医学', '工程'],
    '运动员':  ['体育', '竞技', '运动', '武术', '健身'],
}


# ============================================================
# 字段检查
# ============================================================

def check_completeness(reading):
    """检查必要字段是否存在且非空"""
    r = reading.get('reading', {})
    missing = []
    empty   = []

    for field in REQUIRED_FIELDS:
        if field not in r:
            missing.append(field)
        elif r[field] is None or r[field] == '' or r[field] == []:
            empty.append(field)

    # life_phases 至少要有1条
    phases = r.get('life_phases', [])
    if not isinstance(phases, list) or len(phases) == 0:
        empty.append('life_phases(empty)')

    # personality_traits 至少3条
    traits = r.get('personality_traits', [])
    if not isinstance(traits, list) or len(traits) < 2:
        empty.append('personality_traits(too_few)')

    return missing, empty


def check_day_master_consistency(reading, source_data_map):
    """
    对比研读的日主判断与排盘引擎结果。
    source_data_map: {id -> record} from unified_people_with_bazi.json
    """
    rid = reading.get('id')
    r   = reading.get('reading', {})
    llm_dm = r.get('day_master', '').strip()

    original = source_data_map.get(rid)
    if not original:
        return None, 'record_not_found'

    engine_dm = original.get('bazi', {}).get('day_master', '')

    if not llm_dm:
        return False, 'llm_dm_missing'
    if not engine_dm:
        return None, 'engine_dm_missing'
    if llm_dm == engine_dm:
        return True, None
    return False, f'llm={llm_dm} engine={engine_dm}'


def check_career_match(reading, source_data_map):
    """
    粗粒度检查职业预测与实际职业的关键词重叠。
    """
    rid        = reading.get('id')
    r          = reading.get('reading', {})
    def _to_str(v):
        if isinstance(v, list):
            return ' '.join(str(x) for x in v)
        return v or ''
    career_txt = _to_str(r.get('career_tendency')) + ' ' + _to_str(r.get('career_reasoning'))
    career_txt = career_txt.lower()

    original = source_data_map.get(rid)
    if not original:
        return None

    actual_occs = original.get('occupation', [])
    if not actual_occs:
        return None

    for occ in actual_occs:
        keywords = CAREER_KEYWORD_MAP.get(occ, [])
        if any(kw in career_txt for kw in keywords):
            return True
    return False


# ============================================================
# 主检查流程
# ============================================================

def validate(readings_path, source_path):
    with open(readings_path, 'r', encoding='utf-8') as f:
        readings = json.load(f)

    with open(source_path, 'r', encoding='utf-8') as f:
        source_data = json.load(f)

    source_map = {r['id']: r for r in source_data}

    total = len(readings)
    print(f"研读条数: {total}")

    # --- 完整性 ---
    completeness_results = []
    all_missing = Counter()
    all_empty   = Counter()

    for rdg in readings:
        missing, empty = check_completeness(rdg)
        completeness_results.append((rdg['id'], missing, empty))
        for m in missing:
            all_missing[m] += 1
        for e in empty:
            all_empty[e] += 1

    complete_count = sum(1 for _, m, e in completeness_results if not m and not e)

    # --- 日主一致性 ---
    dm_match   = 0
    dm_mismatch = 0
    dm_unknown = 0
    dm_errors  = []

    for rdg in readings:
        ok, err = check_day_master_consistency(rdg, source_map)
        if ok is True:
            dm_match += 1
        elif ok is False:
            dm_mismatch += 1
            dm_errors.append({'id': rdg['id'], 'name': rdg.get('name_en'), 'error': err})
        else:
            dm_unknown += 1

    # --- 置信度分布 ---
    confidences = []
    for rdg in readings:
        c = rdg.get('reading', {}).get('confidence')
        if isinstance(c, (int, float)):
            confidences.append(float(c))

    conf_buckets = Counter()
    for c in confidences:
        bucket = f"{int(c*10)*10}-{int(c*10)*10+9}%"
        conf_buckets[bucket] += 1

    avg_conf = sum(confidences) / len(confidences) if confidences else 0

    # --- 职业匹配率 ---
    career_true  = 0
    career_false = 0
    career_na    = 0

    for rdg in readings:
        result = check_career_match(rdg, source_map)
        if result is True:
            career_true += 1
        elif result is False:
            career_false += 1
        else:
            career_na += 1

    career_checked = career_true + career_false
    career_match_rate = career_true / career_checked if career_checked > 0 else 0

    # --- 强弱分布 ---
    strength_dist = Counter()
    for rdg in readings:
        s = rdg.get('reading', {}).get('day_master_strength', '')
        if s:
            strength_dist[s] += 1

    # --- 格局分布 ---
    pattern_dist = Counter()
    for rdg in readings:
        p = rdg.get('reading', {}).get('pattern', '')
        if p:
            pattern_dist[p] += 1

    # --- 数据源分布 ---
    source_dist = Counter()
    for rdg in readings:
        src = rdg.get('source', 'unknown')
        source_dist[src] += 1

    # ============================================================
    # 报告输出
    # ============================================================
    print("\n" + "=" * 60)
    print("研读质量报告")
    print("=" * 60)

    print(f"\n✅ 字段完整性:")
    print(f"   完整: {complete_count}/{total} ({complete_count/total*100:.1f}%)")
    if all_missing:
        print(f"   缺失字段: {dict(all_missing.most_common(5))}")
    if all_empty:
        print(f"   空值字段: {dict(all_empty.most_common(5))}")

    print(f"\n☯️ 日主一致性（与排盘引擎对比）:")
    print(f"   一致: {dm_match}  不一致: {dm_mismatch}  无法比对: {dm_unknown}")
    if dm_match + dm_mismatch > 0:
        acc = dm_match / (dm_match + dm_mismatch) * 100
        print(f"   准确率: {acc:.1f}%")
    if dm_errors[:3]:
        print(f"   不一致示例:")
        for e in dm_errors[:3]:
            print(f"     {e['name']}: {e['error']}")

    print(f"\n📊 置信度分布 (平均={avg_conf:.2f}):")
    for bucket in sorted(conf_buckets.keys()):
        bar = '█' * (conf_buckets[bucket] * 30 // max(conf_buckets.values()))
        print(f"   {bucket:10s} {conf_buckets[bucket]:4d} {bar}")

    print(f"\n👔 职业预测匹配率:")
    print(f"   匹配: {career_true}  不匹配: {career_false}  无法判断: {career_na}")
    if career_checked > 0:
        print(f"   关键词匹配率: {career_match_rate*100:.1f}%")

    print(f"\n💪 日主强弱分布:")
    for s, c in strength_dist.most_common():
        print(f"   {s:8s} {c:4d}")

    print(f"\n🏛️ 格局分布 Top 10:")
    for p, c in pattern_dist.most_common(10):
        print(f"   {p:20s} {c:4d}")

    print(f"\n📦 数据源分布:")
    for src, c in source_dist.most_common():
        print(f"   {src:20s} {c:4d}")

    # 保存报告
    report = {
        'total': total,
        'completeness': {
            'complete_count': complete_count,
            'complete_rate':  round(complete_count / total, 4),
            'missing_fields': dict(all_missing),
            'empty_fields':   dict(all_empty),
        },
        'day_master_accuracy': {
            'match':    dm_match,
            'mismatch': dm_mismatch,
            'unknown':  dm_unknown,
            'accuracy': round(dm_match / (dm_match + dm_mismatch), 4) if (dm_match + dm_mismatch) > 0 else None,
            'mismatch_examples': dm_errors[:10],
        },
        'confidence': {
            'average': round(avg_conf, 4),
            'distribution': dict(conf_buckets),
        },
        'career_match': {
            'match':      career_true,
            'no_match':   career_false,
            'na':         career_na,
            'match_rate': round(career_match_rate, 4),
        },
        'strength_distribution': dict(strength_dist),
        'pattern_distribution':  dict(pattern_dist.most_common(20)),
        'source_distribution':   dict(source_dist),
    }

    report_path = DATA_DIR / 'reading_quality_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📊 报告已保存: {report_path}")

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description='研读质量检查')
    parser.add_argument('--readings', default=str(DATA_DIR / 'bazi_readings.json'),
                        help='研读结果文件路径')
    parser.add_argument('--source', default=str(DATA_DIR / 'unified_people_with_bazi.json'),
                        help='原始排盘数据路径')
    args = parser.parse_args()

    readings_path = Path(args.readings)
    source_path   = Path(args.source)

    if not readings_path.exists():
        print(f"❌ 找不到研读文件: {readings_path}")
        print(f"   请先运行: python3 scripts/auto_reader.py")
        sys.exit(1)

    validate(readings_path, source_path)


if __name__ == '__main__':
    main()
