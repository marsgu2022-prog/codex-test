"""
皇极经世 — 元会运世计算器
Layer 1（高置信度，无流派争议）：纯数学位置计算

仅实现：输入公历年份 → 输出元/会/运/世/年的精确位置 + 会卦主题。
不涉及既济图、挂一图、协位变卦等有争议的高层级。

数据来源：
  - 邵雍《皇极经世》原著
  - 韩立研究文档：yuan_starting_year_research.md / hexagram_configuration.md
  - 海云青飞推算：一元起点为公元前67,017年（甲子年）
  - 《四库全书总目》："起于帝尧甲辰，至后周显德六年己未"

设计说明：
  - 一元起点(-67017)是主计算基准，基于"王莽建国元年(公元9年)对应皇极历67026年"反推
  - 经世起点(-2577)和尧即位(-2357)作为辅助参考点，不影响位置计算
  - 十二消息卦对应以标准为准：子=复、丑=临、寅=泰、卯=大壮、辰=夬、巳=乾、
    午=姤、未=遁、申=否、酉=观、戌=剥、亥=坤
  - README文件中"午会=乾"为笔误，已在此处更正
"""

# ============================================================
# 常数
# ============================================================

# 时间层级（无争议）
YUAN = 129600   # 1元 = 129,600年
HUI  = 10800    # 1会 = 10,800年（1元 = 12会）
YUN  = 360      # 1运 = 360年（1会 = 30运）
SHI  = 30       # 1世 = 30年（1运 = 12世）

# 参考起点（支持多起点查询）
REFERENCE_POINTS = {
    "yuan_origin":    -67017,  # 一元起点，公元前67,017年（甲子年）— 主计算基准
    "jingshi_origin": -2577,   # 经世起点，公元前2,577年（甲子年，2149世之始）
    "yao_accession":  -2357,   # 尧即位，公元前2,357年（甲辰年）
}
DEFAULT_REFERENCE = "yuan_origin"  # 默认用一元起点计算

# 地支列表（用于会名）
BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 十二消息卦与十二会的对应（标准：复临泰大壮夬乾姤遁否观剥坤，对应子丑寅卯辰巳午未申酉戌亥）
# 来源：标准十二消息卦理论，非README文件（README中"午会=乾"为笔误）
TWELVE_HUI = [
    {
        "index": 0, "branch": "子", "name": "子会",
        "gua": "复",  "symbol": "䷗",
        "theme": "开天",   "yang": 1, "yin": 5,
        "desc": "一阳初生，混沌初开，天地初辟",
        "trend": "蓄势待发，静待时机",
    },
    {
        "index": 1, "branch": "丑", "name": "丑会",
        "gua": "临",  "symbol": "䷒",
        "theme": "辟地",   "yang": 2, "yin": 4,
        "desc": "二阳生，天地定位，万物萌动",
        "trend": "根基渐稳，缓步前行",
    },
    {
        "index": 2, "branch": "寅", "name": "寅会",
        "gua": "泰",  "symbol": "䷊",
        "theme": "生人",   "yang": 3, "yin": 3,
        "desc": "三阳开泰，万物生发，人类起源",
        "trend": "阴阳平衡，万物皆宜",
    },
    {
        "index": 3, "branch": "卯", "name": "卯会",
        "gua": "大壮", "symbol": "䷡",
        "theme": "文明初创", "yang": 4, "yin": 2,
        "desc": "四阳壮盛，文明初创，八卦始作",
        "trend": "阳气主导，锐意进取",
    },
    {
        "index": 4, "branch": "辰", "name": "辰会",
        "gua": "夬",  "symbol": "䷪",
        "theme": "制度建立", "yang": 5, "yin": 1,
        "desc": "五阳决进，农耕兴起，王朝建立",
        "trend": "阳主阴从，强势扩张",
    },
    {
        "index": 5, "branch": "巳", "name": "巳会",
        "gua": "乾",  "symbol": "䷀",
        "theme": "极盛",   "yang": 6, "yin": 0,
        "desc": "六阳纯极，天行健，文明鼎盛",
        "trend": "盛极将衰，宜居安思危",
    },
    {
        "index": 6, "branch": "午", "name": "午会",
        "gua": "姤",  "symbol": "䷫",
        "theme": "一阴初生", "yang": 5, "yin": 1,
        "desc": "盛极生阴，天下有风，阴始萌于下，变革暗流涌动",
        "trend": "盛中有变，顺势而为",
    },
    {
        "index": 7, "branch": "未", "name": "未会",
        "gua": "遁",  "symbol": "䷠",
        "theme": "退避",   "yang": 4, "yin": 2,
        "desc": "二阴生，退避隐居，文明收缩",
        "trend": "守成为要，不宜冒进",
    },
    {
        "index": 8, "branch": "申", "name": "申会",
        "gua": "否",  "symbol": "䷋",
        "theme": "闭塞",   "yang": 3, "yin": 3,
        "desc": "三阴生，天地不交，万物晦涩",
        "trend": "阴阳不通，宜蛰伏待变",
    },
    {
        "index": 9, "branch": "酉", "name": "酉会",
        "gua": "观",  "symbol": "䷓",
        "theme": "观察",   "yang": 2, "yin": 4,
        "desc": "四阴生，观察等待，文明收藏",
        "trend": "静观其变，不轻举妄动",
    },
    {
        "index": 10, "branch": "戌", "name": "戌会",
        "gua": "剥",  "symbol": "䷖",
        "theme": "剥落",   "yang": 1, "yin": 5,
        "desc": "五阴生，一阳将尽，文明凋零",
        "trend": "固守根本，一阳尚存",
    },
    {
        "index": 11, "branch": "亥", "name": "亥会",
        "gua": "坤",  "symbol": "䷁",
        "theme": "闭物",   "yang": 0, "yin": 6,
        "desc": "六阴纯极，万物归藏，等待新元",
        "trend": "归藏待机，新元将启",
    },
]


# ============================================================
# 核心计算
# ============================================================

def _decompose(years_elapsed: int) -> dict:
    """
    将距离一元起点的年数分解为元/会/运/世/年位置。

    返回 0-indexed 的内部计算结果（yuan/hui 0-indexed，yun/shi/year 0-indexed）。
    """
    n = years_elapsed

    yuan         = n // YUAN
    r            = n % YUAN

    hui          = r // HUI
    r            = r % HUI

    yun_in_hui   = r // YUN
    r            = r % YUN

    shi_in_yun   = r // SHI
    year_in_shi  = r % SHI

    # 绝对运数（1-indexed，从一元起点算）
    yun_absolute = yuan * 360 + hui * 30 + yun_in_hui + 1

    # 绝对世数（1-indexed，从一元起点算）
    shi_absolute = (yun_absolute - 1) * 12 + shi_in_yun + 1

    return {
        "yuan":         yuan,
        "hui":          hui,
        "yun_in_hui":   yun_in_hui,
        "shi_in_yun":   shi_in_yun,
        "year_in_shi":  year_in_shi,
        "yun_absolute": yun_absolute,
        "shi_absolute": shi_absolute,
    }


def calculate_huangji(year: int, reference: str = DEFAULT_REFERENCE) -> dict:
    """
    计算某公历年份在皇极经世体系中的精确位置。

    参数：
        year      — 公历年份（公元前用负数，如 -2357 表示公元前2357年）
        reference — 参考起点键名（"yuan_origin" / "jingshi_origin" / "yao_accession"）

    返回：标准化结果 dict（详见模块文档）

    数据来源：邵雍《皇极经世》；海云青飞推算（一元起点）
    """
    if reference not in REFERENCE_POINTS:
        raise ValueError(f"未知参考点: {reference}，可选：{list(REFERENCE_POINTS.keys())}")

    yuan_origin = REFERENCE_POINTS["yuan_origin"]  # 始终用一元起点做位置计算
    ref_year    = REFERENCE_POINTS[reference]

    years_from_yuan = year - yuan_origin
    if years_from_yuan < 0:
        raise ValueError(f"年份 {year} 早于一元起点 {yuan_origin}")

    pos = _decompose(years_from_yuan)

    hui_data = TWELVE_HUI[pos["hui"]]

    # 当前会/运/世的起始和结束公历年
    hui_start = yuan_origin + pos["yuan"] * YUAN + pos["hui"] * HUI
    hui_end   = hui_start + HUI - 1

    yun_start = hui_start + pos["yun_in_hui"] * YUN
    yun_end   = yun_start + YUN - 1

    shi_start = yun_start + pos["shi_in_yun"] * SHI
    shi_end   = shi_start + SHI - 1

    return {
        "input": {
            "year":           year,
            "reference":      reference,
            "reference_year": ref_year,
        },
        "position": {
            "yuan":          pos["yuan"],
            "hui":           pos["hui"],
            "hui_name":      hui_data["name"],
            "yun":           pos["yun_in_hui"] + 1,   # 1-indexed，该会内第几运
            "yun_absolute":  pos["yun_absolute"],
            "shi":           pos["shi_in_yun"] + 1,   # 1-indexed，该运内第几世
            "shi_absolute":  pos["shi_absolute"],
            "year_in_shi":   pos["year_in_shi"],       # 0-indexed，该世内第几年（0=首年）
            "years_from_ref": year - ref_year,
        },
        "hui_theme": {
            "gua_name":    hui_data["gua"],
            "gua_symbol":  hui_data["symbol"],
            "theme":       hui_data["theme"],
            "description": hui_data["desc"],
            "yang_count":  hui_data["yang"],
            "yin_count":   hui_data["yin"],
            "trend":       hui_data["trend"],
        },
        "context": {
            "shi_start_year": shi_start,
            "shi_end_year":   shi_end,
            "yun_start_year": yun_start,
            "yun_end_year":   yun_end,
            "hui_start_year": hui_start,
            "hui_end_year":   hui_end,
        },
    }


# ============================================================
# 产品接口
# ============================================================

def get_era_description(year: int) -> str:
    """
    产品解读层接口：给BaziChart.ai用的一句话时代背景描述。

    输出示例：
        "2026年处于午会姤卦当令期（5阳1阴），一阴初生于极盛之中，
         文明仍在高峰但变革暗流已起。顺势而为，把握变革窗口。"

    用途：塞入八字解读的"时代背景"段落，用户无需了解皇极经世体系。
    """
    r = calculate_huangji(year)
    pos  = r["position"]
    hui  = r["hui_theme"]
    ctx  = r["context"]

    yang_yin = f"{hui['yang_count']}阳{hui['yin_count']}阴"
    shi_range = f"公历{ctx['shi_start_year']}—{ctx['shi_end_year']}年"

    shi_word = '\u4e16'  # 世
    return (
        f"{year}年处于{pos['hui_name']}{hui['gua_name']}卦当令期（{yang_yin}），"
        f"{hui['description']}。"
        f"当前所处{shi_word}（{shi_range}），{hui['trend']}。"
    )


# ============================================================
# 命令行验证
# ============================================================

def _fmt_year(y: int) -> str:
    """格式化年份：负数显示为'公元前N年'"""
    return f"公元前{-y}年" if y < 0 else f"公元{y}年"


def _print_result(r: dict) -> None:
    pos = r["position"]
    hui = r["hui_theme"]
    ctx = r["context"]
    inp = r["input"]

    print(f"\n  输入年份：{_fmt_year(inp['year'])}  参考点：{inp['reference']}({_fmt_year(inp['reference_year'])})")
    print(f"  元：第{pos['yuan']}元  会：第{pos['hui']}会（{pos['hui_name']} {hui['gua_name']}卦 {hui['gua_symbol']}）")
    print(f"  运：该会第{pos['yun']}运（第{pos['yun_absolute']}绝对运）  "
          f"世：该运第{pos['shi']}世（第{pos['shi_absolute']}绝对世）  年内第{pos['year_in_shi']}年")
    print(f"  会卦：{hui['theme']} — {hui['description']}")
    print(f"  趋势：{hui['trend']}")
    print(f"  当前世：{_fmt_year(ctx['shi_start_year'])} — {_fmt_year(ctx['shi_end_year'])}")
    print(f"  当前运：{_fmt_year(ctx['yun_start_year'])} — {_fmt_year(ctx['yun_end_year'])}")
    print(f"  当前会：{_fmt_year(ctx['hui_start_year'])} — {_fmt_year(ctx['hui_end_year'])}")


def main() -> None:
    print("\n" + "=" * 60)
    print("皇极经世 — 元会运世计算器验证")
    print("=" * 60)

    test_cases = [
        (-67017, "一元起点（应在第0元第0会子会第0世第0年）"),
        (-2577,  "经世起点（应在午会内，2149世附近）"),
        (-2357,  "尧即位甲辰年（应在午会内）"),
        (960,    "宋太祖建隆元年（应在午会内）"),
        (2026,   "当前年份（应在午会姤卦）"),
    ]

    yuan_origin = REFERENCE_POINTS["yuan_origin"]

    for year, desc in test_cases:
        print(f"\n【{desc}】")
        try:
            r = calculate_huangji(year)
            _print_result(r)
        except ValueError as e:
            print(f"  ❌ {e}")

    print("\n" + "-" * 60)
    print("产品接口 get_era_description 示例：")
    print(get_era_description(2026))
    print()


if __name__ == "__main__":
    main()
