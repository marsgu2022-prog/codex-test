"""
八字特征提取器 — BaZi Feature Extractor for ML

从 unified_people_with_bazi.json 提取结构化特征，输出：
- data/training_features.json  — 带特征的完整数据
- data/feature_vectors.csv     — 纯数值矩阵（sklearn ready）
- data/feature_stats.json      — 特征统计报告
"""

import json
import csv
import math
import sys
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent.parent / 'data'

# ============================================================
# 常量
# ============================================================

HEAVENLY_STEMS   = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
EARTHLY_BRANCHES = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']

ELEMENTS     = ['wood', 'fire', 'earth', 'metal', 'water']
ELEMENT_IDX  = {e: i for i, e in enumerate(ELEMENTS)}

TEN_GODS     = ['比肩','劫财','食神','伤官','偏财','正财','偏官','正官','偏印','正印']
TEN_GODS_IDX = {g: i for i, g in enumerate(TEN_GODS)}
# 原数据用"七杀"，统一映射到"偏官"
TEN_GODS_NORMALIZE = {'七杀': '偏官'}

STEM_ELEMENT = {
    '甲':'wood','乙':'wood','丙':'fire','丁':'fire',
    '戊':'earth','己':'earth','庚':'metal','辛':'metal',
    '壬':'water','癸':'water',
}
BRANCH_ELEMENT = {
    '子':'water','丑':'earth','寅':'wood','卯':'wood',
    '辰':'earth','巳':'fire','午':'fire','未':'earth',
    '申':'metal','酉':'metal','戌':'earth','亥':'water',
}
STEM_POLARITY = {s: i % 2 for i, s in enumerate(HEAVENLY_STEMS)}  # 0=阳,1=阴

# 月支→季节
BRANCH_SEASON = {
    '寅':'spring','卯':'spring','辰':'spring',
    '巳':'summer','午':'summer','未':'summer',
    '申':'autumn','酉':'autumn','戌':'autumn',
    '亥':'winter','子':'winter','丑':'winter',
}
SEASON_IDX = {'spring':0, 'summer':1, 'autumn':2, 'winter':3}

STRENGTH_IDX = {'弱':0, '中偏弱':1, '中偏强':2, '强':3}

# 天干五合：甲己合土，乙庚合金，丙辛合水，丁壬合木，戊癸合火
STEM_COMBINES = [
    ('甲','己','earth'),('乙','庚','metal'),('丙','辛','water'),
    ('丁','壬','wood'),('戊','癸','fire'),
]

# 地支六合
BRANCH_SIX_COMBINES = [
    ('子','丑'),('寅','亥'),('卯','戌'),('辰','酉'),('巳','申'),('午','未'),
]

# 地支三合局
BRANCH_THREE_COMBINES = [
    ('申','子','辰','water'),('寅','午','戌','fire'),
    ('巳','酉','丑','metal'),('亥','卯','未','wood'),
]

# 地支六冲
BRANCH_SIX_CLASHES = [
    ('子','午'),('丑','未'),('寅','申'),('卯','酉'),('辰','戌'),('巳','亥'),
]

# 天乙贵人（日干→贵人地支）
TIANY_I_LUCKY = {
    '甲':['丑','未'],'乙':['子','申'],'丙':['亥','酉'],
    '丁':['亥','酉'],'戊':['丑','未'],'己':['子','申'],
    '庚':['丑','未'],'辛':['寅','午'],'壬':['卯','巳'],
    '癸':['卯','巳'],
}

# 文昌贵人（日干→文昌地支）
WEN_CHANG = {
    '甲':'巳','乙':'午','丙':'申','丁':'酉','戊':'申',
    '己':'酉','庚':'亥','辛':'子','壬':'寅','癸':'卯',
}

# 驿马（月支/日支→驿马地支）—— 用三合的中间字推
YIMA_MAP = {
    '申':'寅','子':'寅','辰':'寅',  # 水局驿马在寅
    '寅':'申','午':'申','戌':'申',  # 火局驿马在申
    '亥':'巳','卯':'巳','未':'巳',  # 木局驿马在巳
    '巳':'亥','酉':'亥','丑':'亥',  # 金局驿马在亥
}

# 特征向量字段名（顺序固定）
FEATURE_COLUMNS = (
    # 日主
    ['dm_element_wood','dm_element_fire','dm_element_earth','dm_element_metal','dm_element_water']
    # 日主阴阳
    + ['dm_yang']
    # 季节
    + ['season_spring','season_summer','season_autumn','season_winter']
    # 五行计数（归一化到0-8）
    + ['fe_wood','fe_fire','fe_earth','fe_metal','fe_water']
    # 日主强弱（0-3）
    + ['strength']
    # 十神计数
    + [f'tg_{g}' for g in TEN_GODS]
    # 十神熵
    + ['tg_entropy']
    # 主导十神（one-hot）
    + [f'dominant_{g}' for g in TEN_GODS]
    # 天干五合（5个，是否出现）
    + [f'sc_{a}{b}' for a,b,_ in STEM_COMBINES]
    # 地支六合（6个）
    + [f'bc6_{a}{b}' for a,b in BRANCH_SIX_COMBINES]
    # 地支三合（4个）
    + [f'bc3_{w}' for _,_,_,w in BRANCH_THREE_COMBINES]
    # 地支六冲（6个）
    + [f'clash_{a}{b}' for a,b in BRANCH_SIX_CLASHES]
    # 神煞（天乙贵人、文昌、驿马）
    + ['star_tianyi','star_wenchang','star_yima']
    # 有时辰标志
    + ['has_birth_time']
)


# ============================================================
# 特征提取
# ============================================================

def normalize_ten_god(g):
    return TEN_GODS_NORMALIZE.get(g, g)


def get_all_stems_branches(bazi):
    """从八字提取所有天干和地支"""
    stems, branches = [], []
    for key in ('year_pillar','month_pillar','day_pillar','hour_pillar'):
        p = bazi.get(key)
        if p and len(p) == 2:
            stems.append(p[0])
            branches.append(p[1])
    return stems, branches


def get_ten_gods_list(bazi):
    """提取十神列表（天干十神 + 地支藏干十神，展开为列表）"""
    tg = bazi.get('ten_gods', {})
    gods = []

    for key in ('year_stem','month_stem','hour_stem'):
        g = tg.get(key)
        if g and g != '日主':
            gods.append(normalize_ten_god(g))

    for key in ('year_branch','month_branch','day_branch','hour_branch'):
        gs = tg.get(key, [])
        if gs:
            gods.append(normalize_ten_god(gs[0]))  # 只取本气

    return gods


def shannon_entropy(counts):
    """计算十神分布的香农熵（均匀度）"""
    total = sum(counts)
    if total == 0:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    return -sum(p * math.log2(p) for p in probs)


def detect_stem_combines(stems):
    """检测天干五合"""
    found = []
    for a, b, result in STEM_COMBINES:
        if a in stems and b in stems:
            found.append(f'{a}{b}合{result}')
    return found


def detect_branch_six_combines(branches):
    """检测地支六合"""
    found = []
    for a, b in BRANCH_SIX_COMBINES:
        if a in branches and b in branches:
            found.append(f'{a}{b}六合')
    return found


def detect_branch_three_combines(branches):
    """检测地支三合（含半三合：出现任意两支）"""
    found = []
    for b1, b2, b3, result in BRANCH_THREE_COMBINES:
        matched = sum(1 for b in [b1, b2, b3] if b in branches)
        if matched >= 2:
            found.append(f'{b1}{b2}{b3}三合{result}')
    return found


def detect_branch_clashes(branches):
    """检测地支六冲"""
    found = []
    for a, b in BRANCH_SIX_CLASHES:
        if a in branches and b in branches:
            found.append(f'{a}{b}冲')
    return found


def detect_special_stars(day_master, branches):
    """检测特殊神煞"""
    stars = []

    # 天乙贵人
    lucky_branches = TIANY_I_LUCKY.get(day_master, [])
    if any(b in branches for b in lucky_branches):
        stars.append('天乙贵人')

    # 文昌贵人
    wc = WEN_CHANG.get(day_master)
    if wc and wc in branches:
        stars.append('文昌贵人')

    # 驿马（用日支推）
    if branches:
        day_branch = branches[2] if len(branches) > 2 else branches[0]
        yima = YIMA_MAP.get(day_branch)
        if yima and yima in branches:
            stars.append('驿马')

    return stars


def extract_features(record):
    """
    提取单条记录的特征。
    返回 (numeric_vector, categorical_dict, combinations, special_stars)
    """
    bazi = record.get('bazi')
    if not bazi:
        return None

    day_master = bazi.get('day_master', '')
    dm_element = bazi.get('day_master_element', '')
    dm_strength = bazi.get('day_master_strength', '弱')
    fe_count = bazi.get('five_elements_count', {})
    month_pillar = bazi.get('month_pillar', '')
    month_branch = month_pillar[1] if len(month_pillar) == 2 else ''
    has_time = int(bazi.get('has_birth_time', False))

    stems, branches = get_all_stems_branches(bazi)
    gods_list = get_ten_gods_list(bazi)

    # ----- 1. 日主 one-hot -----
    dm_vec = [0] * 5
    if dm_element in ELEMENT_IDX:
        dm_vec[ELEMENT_IDX[dm_element]] = 1

    # ----- 2. 日主阴阳 -----
    dm_yang = 1 - STEM_POLARITY.get(day_master, 0)  # 1=阳,0=阴

    # ----- 3. 季节 one-hot -----
    season = BRANCH_SEASON.get(month_branch, '')
    season_vec = [0] * 4
    if season in SEASON_IDX:
        season_vec[SEASON_IDX[season]] = 1

    # ----- 4. 五行计数 -----
    fe_vec = [fe_count.get(e, 0) for e in ELEMENTS]

    # ----- 5. 日主强弱 -----
    strength_val = STRENGTH_IDX.get(dm_strength, 0)

    # ----- 6. 十神计数 + 熵 -----
    tg_counter = Counter(gods_list)
    tg_vec = [tg_counter.get(g, 0) for g in TEN_GODS]
    tg_entropy = shannon_entropy(tg_vec)

    # ----- 7. 主导十神 one-hot -----
    dominant_god = max(tg_counter, key=tg_counter.get) if tg_counter else ''
    dominant_vec = [0] * len(TEN_GODS)
    if dominant_god in TEN_GODS_IDX:
        dominant_vec[TEN_GODS_IDX[dominant_god]] = 1

    # ----- 8. 组合 -----
    sc = detect_stem_combines(stems)
    bc6 = detect_branch_six_combines(branches)
    bc3 = detect_branch_three_combines(branches)
    clashes = detect_branch_clashes(branches)
    all_combos = sc + bc6 + bc3 + clashes

    sc_vec  = [1 if (a in stems and b in stems) else 0 for a,b,_ in STEM_COMBINES]
    bc6_vec = [1 if (a in branches and b in branches) else 0 for a,b in BRANCH_SIX_COMBINES]
    bc3_vec = [1 if sum(1 for bx in [b1,b2,b3] if bx in branches) >= 2 else 0
               for b1,b2,b3,_ in BRANCH_THREE_COMBINES]
    clash_vec = [1 if (a in branches and b in branches) else 0 for a,b in BRANCH_SIX_CLASHES]

    # ----- 9. 神煞 -----
    stars = detect_special_stars(day_master, branches)
    star_tianyi   = 1 if '天乙贵人' in stars else 0
    star_wenchang = 1 if '文昌贵人' in stars else 0
    star_yima     = 1 if '驿马' in stars else 0

    # ----- 拼接数值向量 -----
    numeric_vector = (
        dm_vec
        + [dm_yang]
        + season_vec
        + fe_vec
        + [strength_val]
        + tg_vec
        + [round(tg_entropy, 4)]
        + dominant_vec
        + sc_vec
        + bc6_vec
        + bc3_vec
        + clash_vec
        + [star_tianyi, star_wenchang, star_yima]
        + [has_time]
    )

    categorical = {
        'day_master':   day_master,
        'element':      dm_element,
        'polarity':     '阳' if dm_yang else '阴',
        'season':       season,
        'strength':     dm_strength,
        'dominant_god': dominant_god,
    }

    return {
        'numeric_vector': numeric_vector,
        'categorical':    categorical,
        'combinations':   all_combos,
        'special_stars':  stars,
    }


# ============================================================
# 统计报告
# ============================================================

def compute_feature_stats(records_with_features):
    """计算特征统计"""
    vecs = [r['features']['numeric_vector']
            for r in records_with_features if r.get('features')]

    if not vecs:
        return {}

    n = len(vecs)
    dim = len(vecs[0])

    # 每个维度的 min/max/mean
    stats = {}
    for i, col in enumerate(FEATURE_COLUMNS):
        vals = [v[i] for v in vecs]
        stats[col] = {
            'min':  min(vals),
            'max':  max(vals),
            'mean': round(sum(vals) / n, 4),
            'nonzero': sum(1 for v in vals if v != 0),
        }

    # 分类特征分布
    cat_dist = {}
    for key in ('day_master','element','polarity','season','strength','dominant_god'):
        cnt = Counter(
            r['features']['categorical'].get(key, '')
            for r in records_with_features if r.get('features')
        )
        cat_dist[key] = dict(cnt.most_common())

    # 组合出现频率
    combo_cnt = Counter()
    for r in records_with_features:
        if r.get('features'):
            for c in r['features']['combinations']:
                combo_cnt[c] += 1

    # 神煞出现频率
    star_cnt = Counter()
    for r in records_with_features:
        if r.get('features'):
            for s in r['features']['special_stars']:
                star_cnt[s] += 1

    return {
        'n_records':      n,
        'feature_dim':    dim,
        'feature_columns': FEATURE_COLUMNS,
        'numeric_stats':  stats,
        'categorical_distribution': cat_dist,
        'combination_frequency': dict(combo_cnt.most_common(20)),
        'special_star_frequency': dict(star_cnt.most_common()),
    }


def print_stats(stats):
    n   = stats['n_records']
    dim = stats['feature_dim']
    print(f"\n特征维度: {dim}")
    print(f"有效记录: {n:,}")

    print("\n📊 分类特征分布:")
    for key, dist in stats['categorical_distribution'].items():
        top = sorted(dist.items(), key=lambda x: -x[1])[:6]
        line = '  '.join(f"{k}:{v}" for k,v in top)
        print(f"  {key:15s} → {line}")

    print("\n🔗 组合特征 Top 10:")
    for combo, cnt in list(stats['combination_frequency'].items())[:10]:
        pct = cnt / n * 100
        print(f"  {combo:20s} {cnt:5,} ({pct:.1f}%)")

    print("\n⭐ 神煞频率:")
    for star, cnt in stats['special_star_frequency'].items():
        pct = cnt / n * 100
        print(f"  {star:12s} {cnt:5,} ({pct:.1f}%)")

    print("\n📐 数值特征统计（非零率前10）:")
    nonzero_top = sorted(
        stats['numeric_stats'].items(),
        key=lambda x: -x[1]['nonzero']
    )[:10]
    for col, s in nonzero_top:
        pct = s['nonzero'] / n * 100
        print(f"  {col:25s} nonzero={s['nonzero']:,} ({pct:.0f}%)  "
              f"mean={s['mean']:.3f}  max={s['max']}")


# ============================================================
# 主流程
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='八字特征提取')
    parser.add_argument('--test', action='store_true', help='只处理前10条')
    args = parser.parse_args()

    print("=" * 60)
    print("八字特征提取器")
    print("=" * 60)

    # 读取数据
    input_path = DATA_DIR / 'unified_people_with_bazi.json'
    print(f"\n📥 读取: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = [r for r in data if r.get('bazi')]
    print(f"  有排盘数据: {len(records):,} 条")

    if args.test:
        records = records[:10]
        print(f"  [测试模式] 只处理 {len(records)} 条")

    # 提取特征
    print(f"\n🔧 提取特征 (向量维度={len(FEATURE_COLUMNS)})...")
    results = []
    failed = 0
    for r in records:
        features = extract_features(r)
        r_out = dict(r)
        if features:
            r_out['features'] = features
        else:
            r_out['features'] = None
            failed += 1
        results.append(r_out)

    success = len(results) - failed
    print(f"  成功: {success:,}  失败: {failed}")

    # 测试模式打印样本
    if args.test:
        print("\n📋 样本特征:")
        for r in results[:3]:
            f = r.get('features', {})
            if f:
                print(f"\n  {r['name_en']} ({r['birth_date']})")
                print(f"    categorical:  {f['categorical']}")
                print(f"    combinations: {f['combinations']}")
                print(f"    stars:        {f['special_stars']}")
                print(f"    vector[:10]:  {f['numeric_vector'][:10]}")
                print(f"    vector dim:   {len(f['numeric_vector'])}")
        return

    # 保存完整特征数据
    feat_path = DATA_DIR / 'training_features.json'
    with open(feat_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 特征数据已保存: {feat_path}")

    # 保存 CSV（只含有特征的记录）
    csv_path = DATA_DIR / 'feature_vectors.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 表头：id + 特征列 + 标签列
        header = ['id', 'name_en', 'birth_date', 'source'] + FEATURE_COLUMNS + ['occupation_first']
        writer.writerow(header)
        for r in results:
            feat = r.get('features')
            if not feat:
                continue
            occ = r.get('occupation', [''])[0] if r.get('occupation') else ''
            row = (
                [r.get('id',''), r.get('name_en',''), r.get('birth_date',''), r.get('source','')]
                + feat['numeric_vector']
                + [occ]
            )
            writer.writerow(row)
    print(f"💾 CSV 特征矩阵已保存: {csv_path}")

    # 统计报告
    stats = compute_feature_stats(results)
    print_stats(stats)

    # 保存统计 JSON
    stats_path = DATA_DIR / 'feature_stats.json'
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"\n📊 统计报告已保存: {stats_path}")


if __name__ == '__main__':
    main()
