"""
八字排盘引擎 — BaZi Four Pillars Calculator

核心功能：
- 年柱：以立春为界换年
- 月柱：以节气为界换月
- 日柱：儒略日算法
- 时柱：日干推时干
- 十神：根据日主与其余七字关系
- 五行分布：统计八字中五行数量
- 日主强弱：简单版（月令+根气）

节气数据来源：data/solar_terms_1900_2100.json
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 基础常量
# ============================================================

HEAVENLY_STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
EARTHLY_BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 六十甲子
SIXTY_JIAZI = []
for i in range(60):
    SIXTY_JIAZI.append(HEAVENLY_STEMS[i % 10] + EARTHLY_BRANCHES[i % 12])

# 天干五行
STEM_ELEMENT = {
    '甲': '木', '乙': '木',
    '丙': '火', '丁': '火',
    '戊': '土', '己': '土',
    '庚': '金', '辛': '金',
    '壬': '水', '癸': '水',
}

# 地支五行
BRANCH_ELEMENT = {
    '子': '水', '丑': '土', '寅': '木', '卯': '木',
    '辰': '土', '巳': '火', '午': '火', '未': '土',
    '申': '金', '酉': '金', '戌': '土', '亥': '水',
}

# 五行英文
ELEMENT_EN = {'木': 'wood', '火': 'fire', '土': 'earth', '金': 'metal', '水': 'water'}

# 天干阴阳：甲丙戊庚壬为阳，乙丁己辛癸为阴
STEM_POLARITY = {s: '阳' if i % 2 == 0 else '阴' for i, s in enumerate(HEAVENLY_STEMS)}

# 地支阴阳
BRANCH_POLARITY = {b: '阳' if i % 2 == 0 else '阴' for i, b in enumerate(EARTHLY_BRANCHES)}

# 地支藏干（本气、中气、余气）
BRANCH_HIDDEN_STEMS = {
    '子': ['癸'],
    '丑': ['己', '癸', '辛'],
    '寅': ['甲', '丙', '戊'],
    '卯': ['乙'],
    '辰': ['戊', '乙', '癸'],
    '巳': ['丙', '庚', '戊'],
    '午': ['丁', '己'],
    '未': ['己', '丁', '乙'],
    '申': ['庚', '壬', '戊'],
    '酉': ['辛'],
    '戌': ['戊', '辛', '丁'],
    '亥': ['壬', '甲'],
}

# 月支对应的节气（用于确定月柱地支）
# 寅月始于立春，卯月始于惊蛰 ...
MONTH_BRANCH_START_TERMS = {
    '立春': '寅', '惊蛰': '卯', '清明': '辰', '立夏': '巳',
    '芒种': '午', '小暑': '未', '立秋': '申', '白露': '酉',
    '寒露': '戌', '立冬': '亥', '大雪': '子', '小寒': '丑',
}

# 节气列表（按月份顺序，从小寒开始一年的节气）
# 用于判断月柱的12个"节"
MONTH_BOUNDARY_TERMS = [
    '小寒', '立春', '惊蛰', '清明', '立夏', '芒种',
    '小暑', '立秋', '白露', '寒露', '立冬', '大雪',
]

# 月干推算表：年干 -> 正月(寅月)天干
# 甲己之年丙作首，乙庚之岁戊为头，
# 丙辛之年寻庚上，丁壬壬寅顺水流，
# 戊癸之年何方求，甲寅之上好追求
YEAR_STEM_TO_MONTH_STEM_BASE = {
    '甲': '丙', '己': '丙',  # 丙寅月起
    '乙': '戊', '庚': '戊',  # 戊寅月起
    '丙': '庚', '辛': '庚',  # 庚寅月起
    '丁': '壬', '壬': '壬',  # 壬寅月起
    '戊': '甲', '癸': '甲',  # 甲寅月起
}

# 时干推算表：日干 -> 子时天干
# 甲己还加甲，乙庚丙作初，
# 丙辛从戊起，丁壬庚子居，
# 戊癸何方发，壬子是真途
DAY_STEM_TO_HOUR_STEM_BASE = {
    '甲': '甲', '己': '甲',  # 甲子时起
    '乙': '丙', '庚': '丙',  # 丙子时起
    '丙': '戊', '辛': '戊',  # 戊子时起
    '丁': '庚', '壬': '庚',  # 庚子时起
    '戊': '壬', '癸': '壬',  # 壬子时起
}

# 十神关系表
# key: (日主五行, 他干五行, 同阴阳)
TEN_GODS_TABLE = {
    # 同我者：比肩（同阴阳）、劫财（异阴阳）
    ('same', True): '比肩',
    ('same', False): '劫财',
    # 我生者：食神（同阴阳）、伤官（异阴阳）
    ('i_produce', True): '食神',
    ('i_produce', False): '伤官',
    # 我克者：偏财（同阴阳）、正财（异阴阳）
    ('i_conquer', True): '偏财',
    ('i_conquer', False): '正财',
    # 克我者：偏官/七杀（同阴阳）、正官（异阴阳）
    ('conquer_me', True): '偏官',
    ('conquer_me', False): '正官',
    # 生我者：偏印（同阴阳）、正印（异阴阳）
    ('produce_me', True): '偏印',
    ('produce_me', False): '正印',
}

# 五行相生相克
PRODUCES = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
CONQUERS = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}

# 月令得令表：日主五行在该月支是否得令
# 得令 = 月支五行生日主 或 月支五行与日主相同
# 这里简化为月支本气藏干

# ============================================================
# 节气数据加载
# ============================================================

_solar_terms_cache = None

def load_solar_terms():
    """加载节气数据"""
    global _solar_terms_cache
    if _solar_terms_cache is not None:
        return _solar_terms_cache

    data_dir = Path(__file__).parent.parent / 'data'
    solar_terms_file = data_dir / 'solar_terms_1900_2100.json'

    with open(solar_terms_file, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    # 将所有节气按日期排序，构建查找表
    all_terms = []
    for year_str, terms in raw.items():
        for term in terms:
            dt = datetime.fromisoformat(term['datetime'].replace('+08:00', ''))
            all_terms.append({
                'name': term['name'],
                'datetime': dt,
                'year': int(year_str),
            })

    all_terms.sort(key=lambda x: x['datetime'])
    _solar_terms_cache = all_terms
    return all_terms


def find_lichun(year):
    """找到指定年份的立春时刻"""
    terms = load_solar_terms()
    for t in terms:
        if t['year'] == year and t['name'] == '立春':
            return t['datetime']
    return None


def find_month_branch(dt):
    """根据出生日期时间确定月支（以节气为界）"""
    terms = load_solar_terms()

    # 只取"节"（非"气"），即月柱边界的12个节气
    boundary_terms = [t for t in terms if t['name'] in MONTH_BOUNDARY_TERMS]

    # 找到dt所在的月份区间
    prev_term = None
    for t in boundary_terms:
        if t['datetime'] > dt:
            break
        prev_term = t

    if prev_term is None:
        return '寅'  # fallback

    return MONTH_BRANCH_START_TERMS[prev_term['name']]


# ============================================================
# 四柱计算
# ============================================================

def calc_year_pillar(dt):
    """
    计算年柱。
    以立春为界：立春前属上一年，立春后（含）属当年。
    """
    year = dt.year
    lichun = find_lichun(year)

    if lichun is None:
        # 节气数据不可用，fallback用公历年
        calc_year = year
    elif dt < lichun:
        calc_year = year - 1
    else:
        calc_year = year

    # 年干支计算：以甲子年为基准
    # 公元4年为甲子年（近似）
    idx = (calc_year - 4) % 60
    return SIXTY_JIAZI[idx], calc_year


def calc_month_pillar(dt, year_stem):
    """
    计算月柱。
    地支由节气决定，天干由年干推算。
    """
    month_branch = find_month_branch(dt)

    # 月干推算
    base_stem = YEAR_STEM_TO_MONTH_STEM_BASE[year_stem]
    base_idx = HEAVENLY_STEMS.index(base_stem)

    # 寅月为正月，月支索引
    branch_idx = EARTHLY_BRANCHES.index(month_branch)
    # 寅=2，所以偏移 = branch_idx - 2（如果<0则+12）
    month_offset = (branch_idx - 2) % 12

    stem_idx = (base_idx + month_offset) % 10
    month_stem = HEAVENLY_STEMS[stem_idx]

    return month_stem + month_branch


def calc_day_pillar(dt):
    """
    计算日柱。
    使用儒略日算法：以已知日期的干支为基准推算。
    基准：1900年1月1日（庚午年丙子月甲辰日）=> 甲辰 = index 40
    实际上用更精确的基准：2000年1月1日 = 甲午日 (index 30 in 60 jiazi)

    修正基准：1900-01-01 对应 甲戌日
    参考多个万年历验证。
    """
    # 基准日期和对应的六十甲子索引
    # 1900-01-31 是 甲辰日 (index=40)（通过 famous_people.json 交叉验证）
    base_date = datetime(1900, 1, 31)
    base_idx = 40  # 甲辰

    delta_days = (dt.replace(hour=0, minute=0, second=0, microsecond=0) -
                  base_date.replace(hour=0, minute=0, second=0, microsecond=0)).days

    idx = (base_idx + delta_days) % 60
    return SIXTY_JIAZI[idx]


def calc_hour_pillar(day_stem, hour):
    """
    计算时柱。
    hour: 0-23
    子时 23:00-00:59, 丑时 01:00-02:59, ...

    注意：23:00开始算次日子时（早子时），这里简化处理为当日子时。
    """
    # 时辰对应地支
    # 子时 23-1, 丑时 1-3, 寅时 3-5, ...
    if hour == 23:
        branch_idx = 0  # 子时（晚子时归入当日）
    else:
        branch_idx = (hour + 1) // 2

    hour_branch = EARTHLY_BRANCHES[branch_idx]

    # 时干推算
    base_stem = DAY_STEM_TO_HOUR_STEM_BASE[day_stem]
    base_idx = HEAVENLY_STEMS.index(base_stem)
    stem_idx = (base_idx + branch_idx) % 10
    hour_stem = HEAVENLY_STEMS[stem_idx]

    return hour_stem + hour_branch


def get_element_relation(day_master_element, other_element):
    """判断日主五行与他干五行的关系"""
    if day_master_element == other_element:
        return 'same'
    elif PRODUCES[day_master_element] == other_element:
        return 'i_produce'
    elif CONQUERS[day_master_element] == other_element:
        return 'i_conquer'
    elif PRODUCES[other_element] == day_master_element:
        return 'produce_me'
    elif CONQUERS[other_element] == day_master_element:
        return 'conquer_me'
    return None


def calc_ten_god(day_master, other_stem):
    """计算十神关系"""
    if day_master == other_stem:
        return '比肩'

    dm_element = STEM_ELEMENT[day_master]
    other_element = STEM_ELEMENT[other_stem]
    dm_polarity = STEM_POLARITY[day_master]
    other_polarity = STEM_POLARITY[other_stem]

    relation = get_element_relation(dm_element, other_element)
    same_polarity = (dm_polarity == other_polarity)

    return TEN_GODS_TABLE.get((relation, same_polarity), '未知')


def calc_five_elements_count(pillars):
    """统计四柱八字的五行分布"""
    count = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}

    for pillar in pillars:
        if pillar and len(pillar) == 2:
            stem, branch = pillar[0], pillar[1]
            count[STEM_ELEMENT[stem]] += 1
            count[BRANCH_ELEMENT[branch]] += 1

    return count


def assess_day_master_strength(day_master, month_branch, five_elements):
    """
    简单版日主强弱判断。
    考虑：
    1. 月令（月支本气是否生扶日主）
    2. 五行计数（同类+生我 vs 异类）
    """
    dm_element = STEM_ELEMENT[day_master]

    # 月令判断
    month_hidden = BRANCH_HIDDEN_STEMS[month_branch]
    month_main_element = STEM_ELEMENT[month_hidden[0]]  # 本气

    month_supports = (
        month_main_element == dm_element or  # 同类
        PRODUCES.get(month_main_element) == dm_element  # 生我
    )

    # 五行计数
    # 同类 = 与日主相同五行
    # 生我 = 生日主的五行
    producing_element = [k for k, v in PRODUCES.items() if v == dm_element][0]
    support_count = five_elements.get(dm_element, 0) + five_elements.get(producing_element, 0)
    total = sum(five_elements.values())
    oppose_count = total - support_count

    if month_supports and support_count >= oppose_count:
        return '强'
    elif not month_supports and support_count < oppose_count:
        return '弱'
    elif month_supports:
        return '中偏强'
    else:
        return '中偏弱'


# ============================================================
# 主计算入口
# ============================================================

def calculate_bazi(birth_date_str, birth_time_str=None):
    """
    计算完整八字。

    Args:
        birth_date_str: "YYYY-MM-DD"
        birth_time_str: "HH:MM" 或 None

    Returns:
        dict with pillars, ten gods, five elements, etc.
    """
    # 解析日期
    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')

    # 解析时间
    has_time = birth_time_str is not None and birth_time_str.strip() != ''
    if has_time:
        parts = birth_time_str.strip().split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        birth_dt = birth_date.replace(hour=hour, minute=minute)
    else:
        birth_dt = birth_date.replace(hour=12)  # 默认正午
        hour = None

    # 年柱
    year_pillar, bazi_year = calc_year_pillar(birth_dt)
    year_stem = year_pillar[0]

    # 月柱
    month_pillar = calc_month_pillar(birth_dt, year_stem)

    # 日柱
    day_pillar = calc_day_pillar(birth_dt)
    day_stem = day_pillar[0]

    # 时柱
    hour_pillar = None
    if has_time:
        hour_pillar = calc_hour_pillar(day_stem, hour)

    # 十神
    ten_gods = {}
    ten_gods['year_stem'] = calc_ten_god(day_stem, year_pillar[0])
    ten_gods['month_stem'] = calc_ten_god(day_stem, month_pillar[0])
    ten_gods['day_stem'] = '日主'
    if hour_pillar:
        ten_gods['hour_stem'] = calc_ten_god(day_stem, hour_pillar[0])

    # 地支藏干十神
    for label, pillar in [('year_branch', year_pillar), ('month_branch', month_pillar),
                          ('day_branch', day_pillar)]:
        branch = pillar[1]
        hidden = BRANCH_HIDDEN_STEMS[branch]
        ten_gods[label] = [calc_ten_god(day_stem, h) for h in hidden]

    if hour_pillar:
        branch = hour_pillar[1]
        hidden = BRANCH_HIDDEN_STEMS[branch]
        ten_gods['hour_branch'] = [calc_ten_god(day_stem, h) for h in hidden]

    # 五行分布
    pillars_list = [year_pillar, month_pillar, day_pillar]
    if hour_pillar:
        pillars_list.append(hour_pillar)
    five_elements = calc_five_elements_count(pillars_list)

    # 日主强弱
    month_branch = month_pillar[1]
    dm_strength = assess_day_master_strength(day_stem, month_branch, five_elements)

    return {
        'year_pillar': year_pillar,
        'month_pillar': month_pillar,
        'day_pillar': day_pillar,
        'hour_pillar': hour_pillar,
        'day_master': day_stem,
        'day_master_element': ELEMENT_EN[STEM_ELEMENT[day_stem]],
        'day_master_strength': dm_strength,
        'ten_gods': ten_gods,
        'five_elements_count': {
            ELEMENT_EN[k]: v for k, v in five_elements.items()
        },
        'has_birth_time': has_time,
    }


# ============================================================
# 验证与测试
# ============================================================

def validate_known_charts():
    """用已知名人八字验证排盘准确性"""
    test_cases = [
        {
            'name': '乔布斯 Steve Jobs',
            'birth_date': '1955-02-24',
            'birth_time': '19:15',
            # 乙未年 戊寅月 丙辰日 戊戌时（通过 famous_people.json 验证）
            'expected_year': '乙未',
            'expected_month': '戊寅',
            'expected_day': '丙辰',
            'expected_hour': '戊戌',
        },
        {
            'name': '邓小平',
            'birth_date': '1904-08-22',
            'birth_time': '09:00',
            # 甲辰年 壬申月 戊子日（通过 famous_people.json 验证）
            'expected_year': '甲辰',
            'expected_month': '壬申',
            'expected_day': '戊子',
            'expected_hour': '丁巳',
        },
        {
            # 用 famous_people.json 中数据交叉验证
            'name': 'Juan Gabriel (1950-01-07)',
            'birth_date': '1950-01-07',
            'birth_time': '12:00',
            'expected_year': '己丑',  # 1950立春前，仍属1949己丑年
            'expected_month': '丁丑',
            'expected_day': '壬寅',
            'expected_hour': '丙午',
        },
    ]

    results = []
    for tc in test_cases:
        bazi = calculate_bazi(tc['birth_date'], tc['birth_time'])
        passed = True
        errors = []

        for pillar_key, expected_key in [
            ('year_pillar', 'expected_year'),
            ('month_pillar', 'expected_month'),
            ('day_pillar', 'expected_day'),
            ('hour_pillar', 'expected_hour'),
        ]:
            if bazi[pillar_key] != tc[expected_key]:
                passed = False
                errors.append(f'{pillar_key}: 期望{tc[expected_key]}，实际{bazi[pillar_key]}')

        results.append({
            'name': tc['name'],
            'passed': passed,
            'errors': errors,
            'bazi': bazi,
        })

        status = '✅' if passed else '❌'
        print(f"{status} {tc['name']}: "
              f"{bazi['year_pillar']} {bazi['month_pillar']} {bazi['day_pillar']} {bazi['hour_pillar']}")
        if errors:
            for e in errors:
                print(f"   ⚠️ {e}")

    return results


if __name__ == '__main__':
    print("=== 八字排盘引擎验证 ===\n")
    validate_known_charts()
