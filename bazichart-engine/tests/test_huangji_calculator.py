"""
皇极经世计算器测试

验证：
1. 核心算法正确性（关键历史年份）
2. 十二会与消息卦映射
3. 上下文起止年计算
4. 产品接口
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.huangji_calculator import (
    calculate_huangji,
    get_era_description,
    REFERENCE_POINTS,
    TWELVE_HUI,
    YUAN, HUI, YUN, SHI,
)

YUAN_ORIGIN = REFERENCE_POINTS["yuan_origin"]  # -67017


# ============================================================
# 一、核心位置计算
# ============================================================

class TestPositionCalc(unittest.TestCase):

    def _pos(self, year, ref="yuan_origin"):
        return calculate_huangji(year, ref)["position"]

    def test_yuan_origin_is_first_position(self):
        """一元起点：第0元，第0会（子会），第1运，第1世，第0年"""
        pos = self._pos(YUAN_ORIGIN)
        self.assertEqual(pos["yuan"],       0)
        self.assertEqual(pos["hui"],        0)
        self.assertEqual(pos["hui_name"],   "子会")
        self.assertEqual(pos["yun"],        1)   # 1-indexed
        self.assertEqual(pos["shi"],        1)   # 1-indexed
        self.assertEqual(pos["year_in_shi"], 0)  # 0-indexed

    def test_jingshi_origin_position(self):
        """经世起点(-2577)：巳会，第2149绝对世"""
        pos = self._pos(-2577)
        self.assertEqual(pos["hui"],      5)
        self.assertEqual(pos["hui_name"], "巳会")
        self.assertEqual(pos["shi_absolute"], 2149)
        self.assertEqual(pos["year_in_shi"],  0)  # 该世第0年（首年）

    def test_yao_accession_position(self):
        """尧即位(-2357)：巳会，第2156绝对世，第10年(该世第11年)"""
        pos = self._pos(-2357)
        self.assertEqual(pos["hui"],      5)
        self.assertEqual(pos["hui_name"], "巳会")
        self.assertEqual(pos["shi_absolute"], 2156)
        self.assertEqual(pos["year_in_shi"],  10)  # 0-indexed = 第11年

    def test_song_taizu_position(self):
        """宋太祖建隆元年(960)：午会，第2266绝对世"""
        pos = self._pos(960)
        self.assertEqual(pos["hui"],      6)
        self.assertEqual(pos["hui_name"], "午会")
        self.assertEqual(pos["shi_absolute"], 2266)

    def test_2026_hui(self):
        """2026年：第6会（午会，姤卦）"""
        pos = self._pos(2026)
        self.assertEqual(pos["hui"],      6)
        self.assertEqual(pos["hui_name"], "午会")

    def test_2026_yun_absolute(self):
        """2026年：绝对运数=192"""
        pos = self._pos(2026)
        self.assertEqual(pos["yun_absolute"], 192)

    def test_2026_yun_in_hui(self):
        """2026年：该会第12运（1-indexed）"""
        pos = self._pos(2026)
        self.assertEqual(pos["yun"], 12)

    def test_2026_shi_in_yun(self):
        """2026年：该运第10世（1-indexed）"""
        pos = self._pos(2026)
        self.assertEqual(pos["shi"], 10)

    def test_2026_year_in_shi(self):
        """2026年：该世第13年（0-indexed）"""
        pos = self._pos(2026)
        self.assertEqual(pos["year_in_shi"], 13)

    def test_years_from_ref_yuan_origin(self):
        """参考点为yuan_origin时，years_from_ref正确"""
        pos = self._pos(2026, "yuan_origin")
        self.assertEqual(pos["years_from_ref"], 2026 - YUAN_ORIGIN)

    def test_years_from_ref_jingshi(self):
        """参考点为jingshi_origin时，years_from_ref=4603"""
        pos = self._pos(2026, "jingshi_origin")
        self.assertEqual(pos["years_from_ref"], 2026 - (-2577))  # 4603


# ============================================================
# 二、时间层级数学不变式
# ============================================================

class TestMathInvariants(unittest.TestCase):

    def test_hui_boundary_exact(self):
        """每会恰好10800年"""
        r1 = calculate_huangji(YUAN_ORIGIN)["context"]["hui_start_year"]
        r2 = calculate_huangji(YUAN_ORIGIN + HUI)["context"]["hui_start_year"]
        self.assertEqual(r2 - r1, HUI)

    def test_yun_boundary_exact(self):
        """每运恰好360年"""
        r1 = calculate_huangji(2026)["context"]["yun_start_year"]
        r2 = calculate_huangji(2026 + YUN)["context"]["yun_start_year"]
        # 如果不跨运边界则差值等于YUN，否则跨运
        # 验证当年处于同一运时差值为0
        r1b = calculate_huangji(2026)["context"]["yun_end_year"]
        self.assertEqual(r1b - r1 + 1, YUN)

    def test_shi_span_30_years(self):
        """每世恰好30年"""
        ctx = calculate_huangji(2026)["context"]
        self.assertEqual(ctx["shi_end_year"] - ctx["shi_start_year"] + 1, SHI)

    def test_yun_span_360_years(self):
        """每运恰好360年"""
        ctx = calculate_huangji(2026)["context"]
        self.assertEqual(ctx["yun_end_year"] - ctx["yun_start_year"] + 1, YUN)

    def test_hui_span_10800_years(self):
        """每会恰好10800年"""
        ctx = calculate_huangji(2026)["context"]
        self.assertEqual(ctx["hui_end_year"] - ctx["hui_start_year"] + 1, HUI)

    def test_yuan_total_is_129600(self):
        """一元 = 12会 × 10800年 = 129600年"""
        self.assertEqual(12 * HUI, YUAN)

    def test_hui_total_yuns(self):
        """一会 = 30运"""
        self.assertEqual(HUI // YUN, 30)

    def test_yun_total_shis(self):
        """一运 = 12世"""
        self.assertEqual(YUN // SHI, 12)


# ============================================================
# 三、十二会与消息卦对应
# ============================================================

class TestHuiGua(unittest.TestCase):
    """验证标准十二消息卦对应关系：复临泰大壮夬乾姤遁否观剥坤"""

    GUA_SEQUENCE = ['复', '临', '泰', '大壮', '夬', '乾', '姤', '遁', '否', '观', '剥', '坤']
    BRANCH_SEQUENCE = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

    def test_twelve_hui_count(self):
        self.assertEqual(len(TWELVE_HUI), 12)

    def test_gua_sequence(self):
        """卦名按标准消息卦顺序"""
        for i, h in enumerate(TWELVE_HUI):
            self.assertEqual(h["gua"], self.GUA_SEQUENCE[i],
                             f"index={i} 期望={self.GUA_SEQUENCE[i]} 实际={h['gua']}")

    def test_branch_sequence(self):
        """地支按子丑寅...顺序"""
        for i, h in enumerate(TWELVE_HUI):
            self.assertEqual(h["branch"], self.BRANCH_SEQUENCE[i])

    def test_wu_hui_is_gou(self):
        """午会（index=6）对应姤卦，非乾卦（README笔误已更正）"""
        wu_hui = TWELVE_HUI[6]
        self.assertEqual(wu_hui["name"],  "午会")
        self.assertEqual(wu_hui["gua"],   "姤")
        self.assertEqual(wu_hui["symbol"], "䷫")

    def test_si_hui_is_qian(self):
        """巳会（index=5）对应乾卦"""
        si_hui = TWELVE_HUI[5]
        self.assertEqual(si_hui["name"], "巳会")
        self.assertEqual(si_hui["gua"],  "乾")

    def test_yang_yin_count(self):
        """阳爻+阴爻=6（每卦6爻）"""
        for h in TWELVE_HUI:
            self.assertEqual(h["yang"] + h["yin"], 6,
                             f"{h['name']}阴阳爻总数应为6")

    def test_yang_increases_first_half(self):
        """前6会（子→巳）阳爻递增（1→6）"""
        for i in range(6):
            self.assertEqual(TWELVE_HUI[i]["yang"], i + 1)

    def test_yin_increases_second_half(self):
        """后6会（午→亥）阴爻递增（1→6）"""
        for i in range(6):
            self.assertEqual(TWELVE_HUI[6 + i]["yin"], i + 1)

    def test_2026_hui_gua(self):
        """2026年处于姤卦当令"""
        r = calculate_huangji(2026)
        self.assertEqual(r["hui_theme"]["gua_name"],  "姤")
        self.assertEqual(r["hui_theme"]["gua_symbol"], "䷫")


# ============================================================
# 四、产品接口
# ============================================================

class TestEraDescription(unittest.TestCase):

    def test_contains_hui_name(self):
        desc = get_era_description(2026)
        self.assertIn("午会", desc)

    def test_contains_gua_name(self):
        desc = get_era_description(2026)
        self.assertIn("姤", desc)

    def test_contains_year(self):
        desc = get_era_description(2026)
        self.assertIn("2026", desc)

    def test_returns_string(self):
        desc = get_era_description(960)
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 20)


# ============================================================
# 五、错误处理
# ============================================================

class TestErrorHandling(unittest.TestCase):

    def test_unknown_reference_raises(self):
        with self.assertRaises(ValueError):
            calculate_huangji(2026, "unknown_ref")

    def test_before_yuan_origin_raises(self):
        with self.assertRaises(ValueError):
            calculate_huangji(-70000)


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
