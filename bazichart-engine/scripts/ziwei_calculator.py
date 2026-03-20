"""
紫微斗数排盘引擎 — ZiWei DouShu Calculator

实现依据：ZIWEI_ANXINGFA_V2.md（飞星派四化，安星法无争议规则）
接口风格与 bazi_calculator.py 保持一致。

用法：
    from scripts.ziwei_calculator import build_ziwei_chart
    chart = build_ziwei_chart(1985, 3, 15, 14.5, '男')
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ── 农历库 ──
try:
    from lunar_python import Lunar, Solar
    _HAS_LUNAR = True
except ImportError:
    _HAS_LUNAR = False

DATA_DIR = Path(__file__).parent.parent / 'data'

# ============================================================
# §0  基础常量
# ============================================================

BRANCHES = ['', '子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
BRANCH_IDX = {b: i for i, b in enumerate(BRANCHES) if i > 0}   # '子'→1 … '亥'→12

STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
STEM_IDX = {s: i for i, s in enumerate(STEMS)}

# 十二宫名：以命宫为起点，逆行排布
PALACE_NAMES = ['命宫', '兄弟', '夫妻', '子女', '财帛', '疾厄',
                '迁移', '交友', '官禄', '田宅', '福德', '父母']

# 四化（飞星派）
SIHUA_TABLE: dict[str, tuple[str, str, str, str]] = {
    '甲': ('廉贞', '破军', '武曲', '太阳'),
    '乙': ('天机', '天梁', '紫微', '太阴'),
    '丙': ('天同', '天机', '文昌', '廉贞'),
    '丁': ('太阴', '天同', '天机', '巨门'),
    '戊': ('贪狼', '太阴', '右弼', '天机'),
    '己': ('武曲', '贪狼', '天梁', '文曲'),
    '庚': ('太阳', '武曲', '太阴', '天同'),
    '辛': ('巨门', '太阳', '文曲', '文昌'),
    '壬': ('天梁', '紫微', '左辅', '武曲'),
    '癸': ('破军', '巨门', '太阴', '贪狼'),
}

# §3.1 五虎遁：年干→寅宫天干
YEAR_STEM_TO_YIN_STEM = {
    '甲': '丙', '己': '丙',
    '乙': '戊', '庚': '戊',
    '丙': '庚', '辛': '庚',
    '丁': '壬', '壬': '壬',
    '戊': '甲', '癸': '甲',
}

# §4.2 纳音速算
NAYIN_STEM_NUM  = {'甲': 1, '乙': 1, '丙': 2, '丁': 2, '戊': 3,
                   '己': 3, '庚': 4, '辛': 4, '壬': 5, '癸': 5}
NAYIN_BRANCH_NUM = {'子': 1, '丑': 1, '午': 1, '未': 1,
                    '寅': 2, '卯': 2, '申': 2, '酉': 2,
                    '辰': 3, '巳': 3, '戌': 3, '亥': 3}
NAYIN_RESULT = {1: '木', 2: '金', 3: '水', 4: '火', 5: '土'}
JU_MAP = {'水': 2, '木': 3, '金': 4, '土': 5, '火': 6}

# §4.3 六十甲子完整纳音表（双重校验用）
NAYIN_60 = {
    '甲子': '金', '乙丑': '金', '丙寅': '火', '丁卯': '火', '戊辰': '木', '己巳': '木',
    '庚午': '土', '辛未': '土', '壬申': '金', '癸酉': '金', '甲戌': '火', '乙亥': '火',
    '丙子': '水', '丁丑': '水', '戊寅': '土', '己卯': '土', '庚辰': '金', '辛巳': '金',
    '壬午': '木', '癸未': '木', '甲申': '水', '乙酉': '水', '丙戌': '土', '丁亥': '土',
    '戊子': '火', '己丑': '火', '庚寅': '木', '辛卯': '木', '壬辰': '水', '癸巳': '水',
    '甲午': '金', '乙未': '金', '丙申': '火', '丁酉': '火', '戊戌': '木', '己亥': '木',
    '庚子': '土', '辛丑': '土', '壬寅': '金', '癸卯': '金', '甲辰': '火', '乙巳': '火',
    '丙午': '水', '丁未': '水', '戊申': '土', '己酉': '土', '庚戌': '金', '辛亥': '金',
    '壬子': '木', '癸丑': '木', '甲寅': '水', '乙卯': '水', '丙辰': '土', '丁巳': '土',
    '戊午': '火', '己未': '火', '庚申': '木', '辛酉': '木', '壬戌': '水', '癸亥': '水',
}

# §7.1 禄存宫位
LUCUN_IDX = {'甲': 3, '乙': 4, '丙': 6, '丁': 7, '戊': 6,
             '己': 7, '庚': 9, '辛': 10, '壬': 12, '癸': 1}

# §7.3 天魁天钺
KUI_YUE = {
    ('甲', '戊', '庚'): (2, 8),
    ('乙', '己'):       (1, 9),
    ('丙', '丁'):       (12, 10),
    ('辛',):            (7, 3),
    ('壬', '癸'):       (4, 6),
}

# §7.6 火星铃星起始宫
HUO_LING_START = {
    ('寅', '午', '戌'): (2, 4),
    ('申', '子', '辰'): (3, 11),
    ('巳', '酉', '丑'): (4, 11),
    ('亥', '卯', '未'): (10, 11),
}

# §7.8 天马
TIANMA_IDX = {
    ('寅', '午', '戌'): 9,
    ('申', '子', '辰'): 3,
    ('巳', '酉', '丑'): 12,
    ('亥', '卯', '未'): 6,
}

# 阳年干
YANG_STEMS = {'甲', '丙', '戊', '庚', '壬'}


# ============================================================
# §0  工具函数
# ============================================================

def normalize(i: int) -> int:
    """将任意整数归一化到 1-12（宫位索引）"""
    while i <= 0:
        i += 12
    while i > 12:
        i -= 12
    return i


def _lookup_tables() -> dict:
    path = DATA_DIR / 'ziwei_lookup_tables.json'
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


_TABLES_CACHE: dict | None = None


def _get_tables() -> dict:
    global _TABLES_CACHE
    if _TABLES_CACHE is None:
        _TABLES_CACHE = _lookup_tables()
    return _TABLES_CACHE


# ============================================================
# §1  预处理
# ============================================================

def get_hour_branch(h_float: float) -> tuple[int, str]:
    """
    §1.2 时辰地支。
    23:00-01:00=子(0), 01:00-03:00=丑(1) …
    返回 (hour_idx 0-11, branch_name)
    """
    h = h_float % 24
    if h >= 23 or h < 1:
        idx = 0
    else:
        idx = int((h + 1) // 2)
    return idx, BRANCHES[idx + 1]   # BRANCHES[1]='子' … BRANCHES[12]='亥'


def is_late_zishi(h_float: float) -> bool:
    """§1.4 晚子时（23:00-00:00）需将农历日柱进一日"""
    return h_float % 24 >= 23


def solar_to_lunar(year: int, month: int, day: int,
                   advance_day: bool = False
                   ) -> dict[str, Any]:
    """
    §1.2 公历→农历（需 lunar_python 库）。
    advance_day: True 时日期+1天（晚子时用）。

    返回：
        ly, lm, ld      农历年月日（lm 负数=闰月）
        effective_lm    闰月处理后的有效月份（1-12）
        year_stem       年干（立春换年）
        year_branch     年支（立春换年）
        is_leap_month   是否闰月
    """
    if not _HAS_LUNAR:
        raise RuntimeError('需要安装 lunar_python: pip install lunar-python')

    solar_date = Solar.fromYmd(year, month, day)
    if advance_day:
        from datetime import datetime, timedelta
        dt = datetime(year, month, day) + timedelta(days=1)
        solar_date = Solar.fromYmd(dt.year, dt.month, dt.day)

    lunar = solar_date.getLunar()

    lm = lunar.getMonth()          # 负=闰月
    ld = lunar.getDay()
    is_leap = lm < 0

    # §1.3 闰月处理：上半月归前月，下半月归后月
    if is_leap:
        abs_m = abs(lm)
        effective_lm = abs_m if ld <= 15 else normalize_month(abs_m + 1)
    else:
        effective_lm = lm

    year_stem   = lunar.getYearGanByLiChun()
    year_branch = lunar.getYearZhiByLiChun()

    return {
        'ly':            lunar.getYear(),
        'lm':            lm,
        'ld':            ld,
        'effective_lm':  effective_lm,
        'is_leap_month': is_leap,
        'year_stem':     year_stem,
        'year_branch':   year_branch,
    }


def normalize_month(m: int) -> int:
    if m > 12:
        return m - 12
    if m < 1:
        return m + 12
    return m


def apply_longitude_correction(h_float: float, longitude: float) -> float:
    """§1.2 真太阳时校正（可选）"""
    zone_lon = 120.0
    delta = (longitude - zone_lon) / 15.0
    return h_float + delta


# ============================================================
# §2  命宫 / 身宫 / 十二宫排布
# ============================================================

def calc_ming_gong(effective_lm: int, hour_idx: int) -> int:
    """
    §2.2 命宫定位。
    从寅(3)起正月顺行数月，再从该宫逆行数时辰。
    """
    month_pos = normalize(3 + (effective_lm - 1))
    ming_idx  = normalize(month_pos - hour_idx)
    return ming_idx


def calc_shen_gong(effective_lm: int, hour_idx: int) -> int:
    """
    §2.3 身宫定位。
    从月位顺行数时辰。身宫只落在命/夫妻/财帛/迁移/官禄/福德六宫之一。
    """
    month_pos = normalize(3 + (effective_lm - 1))
    shen_idx  = normalize(month_pos + hour_idx)
    return shen_idx


def assign_12_palaces(ming_idx: int) -> dict[int, str]:
    """
    §2.4 以命宫为起点，逆行排布十二宫。
    返回 {palace_branch_idx: palace_name}
    """
    mapping: dict[int, str] = {}
    for i, name in enumerate(PALACE_NAMES):
        idx = normalize(ming_idx - i)
        mapping[idx] = name
    return mapping


# ============================================================
# §3  安宫干（五虎遁）
# ============================================================

def get_yin_stem(year_stem: str) -> str:
    """§3.1 五虎遁：年干→寅宫天干"""
    return YEAR_STEM_TO_YIN_STEM[year_stem]


def assign_palace_stems(year_stem: str) -> dict[int, str]:
    """
    §3.2 从寅宫起顺排十二宫天干。
    宫位顺序：寅(3)→卯(4)→…→丑(2)（地支顺时针循环）
    """
    yin_stem  = get_yin_stem(year_stem)
    start_idx = STEM_IDX[yin_stem]
    # 从寅(3)顺序排到丑(2)，共12宫
    branch_order = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2]
    stems: dict[int, str] = {}
    for i, branch_idx in enumerate(branch_order):
        stems[branch_idx] = STEMS[(start_idx + i) % 10]
    return stems


# ============================================================
# §4  五行局（纳音五行）
# ============================================================

def calc_nayin(stem: str, branch: str) -> str:
    """
    §4.2 纳音五行速算法 + §4.3 完整表双重校验。
    两种方法不一致时抛出 AssertionError。
    """
    # 速算法
    total = NAYIN_STEM_NUM[stem] + NAYIN_BRANCH_NUM[branch]
    if total > 5:
        total -= 5
    fast = NAYIN_RESULT[total]

    # 完整表校验
    key = stem + branch
    if key in NAYIN_60:
        table = NAYIN_60[key]
        assert fast == table, (
            f'纳音双重验证失败：速算={fast} 查表={table} 干支={key}'
        )

    return fast


def get_ju(nayin: str) -> int:
    """§4.1 纳音五行→局数（2-6）"""
    return JU_MAP[nayin]


# ============================================================
# §5  紫微星系安星
# ============================================================

def lookup_ziwei(ju: int, ld: int) -> int:
    """§5.1 查表获取紫微星宫位索引"""
    tables = _get_tables()
    return tables['ziwei'][str(ju)][str(ld)]['index']


def lookup_tianfu(ju: int, ld: int) -> int:
    """§6.1 查表获取天府星宫位索引"""
    tables = _get_tables()
    return tables['tianfu'][str(ju)][str(ld)]['index']


def place_ziwei_system(k: int, palaces: dict[int, dict]) -> None:
    """
    §5.2 紫微星系六颗主星（逆行）。
    口诀：紫微天机星逆行，隔一阳武天同行，天同隔二是廉贞。
    """
    stars = {
        '紫微': normalize(k),
        '天机': normalize(k - 1),
        '太阳': normalize(k - 3),
        '武曲': normalize(k - 4),
        '天同': normalize(k - 5),
        '廉贞': normalize(k - 7),   # k-7 = k+5 (mod 12)
    }
    for star, idx in stars.items():
        palaces[idx]['major_stars'].append(star)


def place_tianfu_system(k: int, palaces: dict[int, dict]) -> None:
    """
    §6.2 天府星系八颗主星（顺行）。
    口诀：天府太阴顺贪狼，巨门天相与天梁，七杀空三是破军。
    """
    stars = {
        '天府': normalize(k),
        '太阴': normalize(k + 1),
        '贪狼': normalize(k + 2),
        '巨门': normalize(k + 3),
        '天相': normalize(k + 4),
        '天梁': normalize(k + 5),
        '七杀': normalize(k + 6),
        '破军': normalize(k + 10),  # k+10 = k-2 (mod 12)
    }
    for star, idx in stars.items():
        palaces[idx]['major_stars'].append(star)


# ============================================================
# §7  辅星安星
# ============================================================

def place_lucun(year_stem: str, palaces: dict) -> int:
    """§7.1 禄存（年干定位）"""
    idx = LUCUN_IDX[year_stem]
    palaces[idx]['aux_stars'].append('禄存')
    return idx


def place_yang_tuo(lucun_idx: int, palaces: dict) -> None:
    """§7.2 擎羊（禄存+1）、陀罗（禄存-1）"""
    palaces[normalize(lucun_idx + 1)]['aux_stars'].append('擎羊')
    palaces[normalize(lucun_idx - 1)]['aux_stars'].append('陀罗')


def place_kui_yue(year_stem: str, palaces: dict) -> None:
    """§7.3 天魁（年干定位）、天钺"""
    for stems_group, (kui_idx, yue_idx) in KUI_YUE.items():
        if year_stem in stems_group:
            palaces[kui_idx]['aux_stars'].append('天魁')
            palaces[yue_idx]['aux_stars'].append('天钺')
            return


def place_zuo_you(effective_lm: int, palaces: dict) -> None:
    """
    §7.4 左辅（辰宫5起正月顺行），右弼（戌宫11起正月逆行）
    """
    zuo_idx = normalize(5 + (effective_lm - 1))
    you_idx = normalize(11 - (effective_lm - 1))
    palaces[zuo_idx]['aux_stars'].append('左辅')
    palaces[you_idx]['aux_stars'].append('右弼')


def place_chang_qu(hour_idx: int, palaces: dict) -> None:
    """
    §7.5 文昌（戌11起子时逆行），文曲（辰5起子时顺行）
    """
    chang_idx = normalize(11 - hour_idx)
    qu_idx    = normalize(5 + hour_idx)
    palaces[chang_idx]['aux_stars'].append('文昌')
    palaces[qu_idx]['aux_stars'].append('文曲')


def place_huo_ling(year_branch: str, hour_idx: int, palaces: dict) -> None:
    """§7.6 火星（顺行）、铃星（顺行），起始宫按年支分组"""
    for branch_group, (huo_start, ling_start) in HUO_LING_START.items():
        if year_branch in branch_group:
            palaces[normalize(huo_start + hour_idx)]['aux_stars'].append('火星')
            palaces[normalize(ling_start + hour_idx)]['aux_stars'].append('铃星')
            return


def place_kong_jie(hour_idx: int, palaces: dict) -> None:
    """§7.7 地空（亥12起子时逆行），地劫（亥12起子时顺行）"""
    palaces[normalize(12 - hour_idx)]['aux_stars'].append('地空')
    palaces[normalize(12 + hour_idx)]['aux_stars'].append('地劫')


def place_tianma(year_branch: str, palaces: dict) -> None:
    """§7.8 天马（年支四组定位）"""
    for branch_group, idx in TIANMA_IDX.items():
        if year_branch in branch_group:
            palaces[idx]['aux_stars'].append('天马')
            return


def place_hong_xi(year_branch: str, palaces: dict) -> None:
    """
    §7.9 红鸾（卯4起子年逆行），天喜（红鸾对宫+6）
    """
    yb_idx   = BRANCH_IDX[year_branch]   # 子=1..亥=12 → 0-based offset
    hong_idx = normalize(4 - (yb_idx - 1))   # 子年(yb_idx=1) → normalize(4-0)=4=卯
    xi_idx   = normalize(hong_idx + 6)
    palaces[hong_idx]['aux_stars'].append('红鸾')
    palaces[xi_idx]['aux_stars'].append('天喜')


# ============================================================
# §8  四化
# ============================================================

def apply_sihua(stem: str, palaces: dict) -> dict[str, dict[str, str]]:
    """
    §8.1-8.2 年干四化落宫（飞星派）。
    返回 {star_name: {palace_idx, sihua_type}} 的字典。
    """
    lu, quan, ke, ji = SIHUA_TABLE[stem]
    result: dict[str, dict] = {}

    for star, sihua_type in [(lu, '禄'), (quan, '权'), (ke, '科'), (ji, '忌')]:
        # 找到该星所在宫
        for idx, p in palaces.items():
            all_stars = p['major_stars'] + p['aux_stars']
            if star in all_stars:
                if 'sihua' not in p:
                    p['sihua'] = {}
                p['sihua'][star] = sihua_type
                result[star] = {'palace_index': idx, 'type': sihua_type}
                break
    return result


# ============================================================
# §9  大限
# ============================================================

def calc_dalim(ming_idx: int, year_stem: str, sex: str, ju: int,
               palace_stems: dict[int, str]) -> dict[str, Any]:
    """
    §9.1-9.4 大限计算。

    返回：
        direction: '顺' 或 '逆'
        start_age: 起始虚岁（=局数）
        decades:   12个大限列表
    """
    is_yang = year_stem in YANG_STEMS
    if (sex == '男' and is_yang) or (sex == '女' and not is_yang):
        direction = 1   # 顺行
        dir_name  = '顺'
    else:
        direction = -1  # 逆行
        dir_name  = '逆'

    start_age = ju

    decades = []
    for n in range(1, 13):
        p_idx   = normalize(ming_idx + direction * (n - 1))
        p_stem  = palace_stems[p_idx]
        age_lo  = start_age + (n - 1) * 10
        age_hi  = age_lo + 9
        # 大限宫干四化
        sihua_lu, sihua_quan, sihua_ke, sihua_ji = SIHUA_TABLE[p_stem]
        decades.append({
            'n':            n,
            'age_range':    f'{age_lo}-{age_hi}',
            'palace_index': p_idx,
            'palace_branch': BRANCHES[p_idx],
            'palace_stem':  p_stem,
            'sihua':        {
                '禄': sihua_lu, '权': sihua_quan,
                '科': sihua_ke, '忌': sihua_ji,
            },
        })

    return {
        'direction':   dir_name,
        'start_age':   start_age,
        'decades':     decades,
    }


# ============================================================
# §附录B  校验
# ============================================================

def validate_chart(chart: dict) -> list[str]:
    """
    对完成命盘做基础校验，返回问题列表（空=通过）。
    """
    issues: list[str] = []
    palaces = chart['palaces']

    # 1. 十四主星总数
    total_major = sum(len(p['major_stars']) for p in palaces.values())
    if total_major != 14:
        issues.append(f'主星总数应为14，实际={total_major}')

    # 2. 数学不变式：双星宫数 = 空星宫数 + 2（由 14星12宫的鸽巢原理推导）
    double_count = sum(1 for p in palaces.values() if len(p['major_stars']) == 2)
    empty_count  = sum(1 for p in palaces.values() if len(p['major_stars']) == 0)
    if double_count != empty_count + 2:
        issues.append(f'双星宫({double_count})应等于空星宫({empty_count})+2，违反14星12宫不变式')

    # 3. 天府与七杀对宫（相隔6宫）
    tianfu_idx = None
    qisha_idx  = None
    for idx, p in palaces.items():
        if '天府' in p['major_stars']:
            tianfu_idx = idx
        if '七杀' in p['major_stars']:
            qisha_idx = idx
    if tianfu_idx and qisha_idx:
        diff = abs(tianfu_idx - qisha_idx)
        diff = min(diff, 12 - diff)
        if diff != 6:
            issues.append(f'天府({tianfu_idx})与七杀({qisha_idx})应对宫，差={diff}')

    # 4. 禄存不与擎羊/陀罗同宫
    for idx, p in palaces.items():
        stars = p['aux_stars']
        if '禄存' in stars and ('擎羊' in stars or '陀罗' in stars):
            issues.append(f'禄存与擎羊/陀罗同宫（宫{idx}），安星有误')

    # 5. 宫干循环：子宫(1)天干=寅宫(3)天干，丑宫(2)天干=卯宫(4)天干
    stems = {idx: p['stem'] for idx, p in palaces.items()}
    if stems.get(1) != stems.get(3):
        issues.append(f'子宫天干({stems.get(1)})≠寅宫天干({stems.get(3)})')
    if stems.get(2) != stems.get(4):
        issues.append(f'丑宫天干({stems.get(2)})≠卯宫天干({stems.get(4)})')

    return issues


# ============================================================
# 主入口
# ============================================================

def build_ziwei_chart(
    year: int, month: int, day: int,
    hour: float,
    sex: str,
    longitude: float | None = None,
) -> dict[str, Any]:
    """
    紫微斗数完整排盘。

    Args:
        year, month, day: 公历出生年月日
        hour: 出生时刻（浮点，如 14.5 = 14:30）
        sex:  '男' 或 '女'
        longitude: 出生地经度（可选，用于真太阳时校正）

    Returns:
        完整命盘 dict
    """
    # ── §1 预处理 ──────────────────────────────────────────
    if longitude is not None:
        hour = apply_longitude_correction(hour, longitude)

    late_zi = is_late_zishi(hour)
    hour_idx, hour_branch = get_hour_branch(hour)

    lunar_info = solar_to_lunar(year, month, day, advance_day=late_zi)

    lm          = lunar_info['lm']
    ld          = lunar_info['ld']
    eff_lm      = lunar_info['effective_lm']
    year_stem   = lunar_info['year_stem']
    year_branch = lunar_info['year_branch']

    # ── §2 命宫 / 身宫 / 十二宫 ────────────────────────────
    ming_idx = calc_ming_gong(eff_lm, hour_idx)
    shen_idx = calc_shen_gong(eff_lm, hour_idx)
    palace_names = assign_12_palaces(ming_idx)

    # ── §3 安宫干 ───────────────────────────────────────────
    palace_stems = assign_palace_stems(year_stem)

    # ── §4 五行局 ───────────────────────────────────────────
    ming_stem   = palace_stems[ming_idx]
    ming_branch = BRANCHES[ming_idx]
    nayin       = calc_nayin(ming_stem, ming_branch)
    ju          = get_ju(nayin)

    # ── 初始化 12 宫数据结构 ─────────────────────────────────
    palaces: dict[int, dict] = {}
    for idx in range(1, 13):
        palaces[idx] = {
            'index':        idx,
            'branch':       BRANCHES[idx],
            'stem':         palace_stems[idx],
            'name':         palace_names.get(idx, ''),
            'major_stars':  [],
            'aux_stars':    [],
            'sihua':        {},
            'is_shen_gong': (idx == shen_idx),
        }

    # ── §5 紫微星系 ─────────────────────────────────────────
    ziwei_idx  = lookup_ziwei(ju, ld)
    place_ziwei_system(ziwei_idx, palaces)

    # ── §6 天府星系 ─────────────────────────────────────────
    tianfu_idx = lookup_tianfu(ju, ld)
    place_tianfu_system(tianfu_idx, palaces)

    # ── §7 辅星 ─────────────────────────────────────────────
    lucun_idx = place_lucun(year_stem, palaces)
    place_yang_tuo(lucun_idx, palaces)
    place_kui_yue(year_stem, palaces)
    place_zuo_you(eff_lm, palaces)
    place_chang_qu(hour_idx, palaces)
    place_huo_ling(year_branch, hour_idx, palaces)
    place_kong_jie(hour_idx, palaces)
    place_tianma(year_branch, palaces)
    place_hong_xi(year_branch, palaces)

    # ── §8 四化 ─────────────────────────────────────────────
    sihua_result = apply_sihua(year_stem, palaces)

    # ── §9 大限 ─────────────────────────────────────────────
    dalim = calc_dalim(ming_idx, year_stem, sex, ju, palace_stems)

    # ── 组装结果 ─────────────────────────────────────────────
    chart: dict[str, Any] = {
        'input': {
            'solar': {'year': year, 'month': month, 'day': day, 'hour': hour},
            'lunar': {
                'year': lunar_info['ly'],
                'month': lm,
                'day': ld,
                'effective_month': eff_lm,
                'is_leap_month': lunar_info['is_leap_month'],
                'is_late_zishi': late_zi,
            },
            'sex': sex,
            'longitude': longitude,
        },
        'ming_gong': {
            'index':  ming_idx,
            'branch': BRANCHES[ming_idx],
            'stem':   ming_stem,
            'name':   '命宫',
        },
        'shen_gong': {
            'index':  shen_idx,
            'branch': BRANCHES[shen_idx],
            'name':   palace_names.get(shen_idx, ''),
        },
        'wu_xing_ju': {
            'ming_ganzhi': ming_stem + ming_branch,
            'nayin':       nayin,
            'ju':          ju,
            'ju_name':     f'{nayin}{ju}局',
        },
        'year_ganzhi': {
            'stem':   year_stem,
            'branch': year_branch,
        },
        'palaces': palaces,
        'sihua':   sihua_result,
        'dalim':   dalim,
    }

    # ── 校验 ─────────────────────────────────────────────────
    issues = validate_chart(chart)
    chart['validation'] = {'passed': len(issues) == 0, 'issues': issues}

    return chart


# ============================================================
# 便利打印函数
# ============================================================

def print_chart(chart: dict) -> None:
    """打印命盘概要"""
    inp   = chart['input']
    solar = inp['solar']
    lunar = inp['lunar']
    print(f"\n{'='*60}")
    print(f"紫微斗数命盘")
    print(f"  公历: {solar['year']}-{solar['month']:02d}-{solar['day']:02d}  时: {solar['hour']}")
    print(f"  农历: {lunar['year']}年 {lunar['month']}月 {lunar['day']}日"
          f"{'(闰月)' if lunar['is_leap_month'] else ''}")
    print(f"  性别: {inp['sex']}")

    wj = chart['wu_xing_ju']
    mg = chart['ming_gong']
    sg = chart['shen_gong']
    print(f"\n  命宫: {mg['branch']}宫({mg['index']}) 宫干:{mg['stem']}")
    print(f"  身宫: {sg['branch']}宫({sg['index']}) 所在:{sg['name']}")
    print(f"  五行局: {wj['ming_ganzhi']} → 纳音{wj['nayin']} → {wj['ju_name']}")

    print(f"\n{'─'*60}")
    print(f"  {'宫':>2} {'宫名':>4} {'干':>2}  主星                    辅星")
    for idx in range(1, 13):
        p = chart['palaces'][idx]
        shen = '★' if p['is_shen_gong'] else ' '
        sihua_str = ' '.join(f"{s}({t})" for s, t in p['sihua'].items())
        print(f"  {p['branch']}{shen} {p['name']:>3} {p['stem']}  "
              f"{' '.join(p['major_stars']):<20} {' '.join(p['aux_stars'])}")

    dl = chart['dalim']
    print(f"\n  大限: {dl['direction']}行  起始:{dl['start_age']}岁")
    for d in dl['decades'][:6]:
        print(f"    第{d['n']}限 {d['age_range']}岁  {d['palace_branch']}宫({d['palace_stem']}干)")

    val = chart['validation']
    status = '✅' if val['passed'] else '❌'
    print(f"\n  校验: {status}", '  '.join(val['issues']) if val['issues'] else '全部通过')
    print('='*60)


# ============================================================
# 命令行快速测试
# ============================================================

if __name__ == '__main__':
    print("=== 紫微斗数排盘引擎验证 ===")

    # 验证案例1：乔布斯 1955-02-24 19:15 男
    # （以此为结构验证，具体命盘需对照排盘软件确认）
    print("\n【测试1】Steve Jobs 1955-02-24 19:15 男")
    c1 = build_ziwei_chart(1955, 2, 24, 19.25, '男')
    print_chart(c1)

    # 验证案例2：闰月边界
    print("\n【测试2】1984-12-05 (闰10月13日，上半月→归10月) 男 午时")
    c2 = build_ziwei_chart(1984, 12, 5, 12.0, '男')
    print_chart(c2)

    # 验证案例3：晚子时
    print("\n【测试3】1990-03-15 23:30 晚子时 女")
    c3 = build_ziwei_chart(1990, 3, 15, 23.5, '女')
    print_chart(c3)
