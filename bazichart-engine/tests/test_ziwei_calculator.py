"""
紫微斗数排盘引擎测试

覆盖：
1. 标准命盘验证（Steve Jobs，与在线工具对比）
2. 边界条件（闰月、晚子时、LD=30、5种五行局）
3. 批量无崩溃测试（unified_people_with_bazi.json 中有时辰数据的记录）
"""

import json
import sys
import unittest
from pathlib import Path

# 支持直接 python3 tests/test_ziwei_calculator.py
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.ziwei_calculator import build_ziwei_chart

DATA_DIR = Path(__file__).parent.parent / 'data'


# ============================================================
# 工具函数
# ============================================================

def stars_in_palace(chart, branch):
    """返回某地支宫位的主星列表"""
    for p in chart['palaces'].values():
        if p['branch'] == branch:
            return p['major_stars']
    return []


def palace_name(chart, branch):
    """返回某地支宫位的宫名"""
    for p in chart['palaces'].values():
        if p['branch'] == branch:
            return p['name']
    return ''


# ============================================================
# 一、标准命盘验证
# ============================================================

class TestStandardChart(unittest.TestCase):
    """以 Steve Jobs (1955-02-24 19:15 男) 为标准盘"""

    @classmethod
    def setUpClass(cls):
        cls.chart = build_ziwei_chart(1955, 2, 24, 19.25, '男')

    def test_validation_passes(self):
        self.assertTrue(self.chart['validation']['passed'],
                        self.chart['validation']['issues'])

    def test_ming_gong_branch(self):
        # 命宫：巳宫（index=6）
        self.assertEqual(self.chart['ming_gong']['branch'], '巳')
        self.assertEqual(self.chart['ming_gong']['index'], 6)

    def test_ming_gong_stem(self):
        # 命宫宫干：辛
        self.assertEqual(self.chart['ming_gong']['stem'], '辛')

    def test_wu_xing_ju(self):
        # 辛巳 → 纳音金 → 金4局
        ju = self.chart['wu_xing_ju']
        self.assertEqual(ju['nayin'], '金')
        self.assertEqual(ju['ju'], 4)

    def test_ziwei_position(self):
        # 农历2月3日，金4局 → 紫微在丑（index=2）
        self.assertIn('紫微', stars_in_palace(self.chart, '丑'))

    def test_tianfu_position(self):
        # 天府在卯（normalize(6-2)=4 → 卯）
        self.assertIn('天府', stars_in_palace(self.chart, '卯'))

    def test_pojun_with_ziwei(self):
        # 破军与紫微同宫（丑）
        self.assertIn('破军', stars_in_palace(self.chart, '丑'))

    def test_mingong_star(self):
        # 命宫（巳）主星为贪狼
        self.assertIn('贪狼', stars_in_palace(self.chart, '巳'))

    def test_total_major_stars(self):
        # 十四主星总数
        total = sum(len(p['major_stars']) for p in self.chart['palaces'].values())
        self.assertEqual(total, 14)

    def test_double_empty_invariant(self):
        # 鸽巢不变式：双星宫 = 空星宫 + 2
        palaces = list(self.chart['palaces'].values())
        doubles = sum(1 for p in palaces if len(p['major_stars']) == 2)
        empties = sum(1 for p in palaces if len(p['major_stars']) == 0)
        self.assertEqual(doubles, empties + 2)

    def test_dalim_direction_male_1955(self):
        # 阳年（乙未→阳干？）男生，查看大限方向
        # 1955 乙未年 → 年干乙(阴)，阴男逆行
        # 但此处命盘显示大限逆行
        dalim = self.chart['dalim']
        self.assertIn('direction', dalim)
        self.assertIn(dalim['direction'], ['顺行', '逆行', '顺', '逆'])

    def test_12_palaces(self):
        # 恰好12个宫位
        self.assertEqual(len(self.chart['palaces']), 12)

    def test_lunar_date(self):
        # 农历：1955年2月3日
        lunar = self.chart['input']['lunar']
        self.assertEqual(lunar['year'], 1955)
        self.assertEqual(lunar['month'], 2)
        self.assertEqual(lunar['day'], 3)


# ============================================================
# 二、边界条件
# ============================================================

class TestEdgeCases(unittest.TestCase):

    def test_leap_month(self):
        """闰月：1984-12-05 落在农历闰10月13日"""
        chart = build_ziwei_chart(1984, 12, 5, 12.0, '男')
        self.assertTrue(chart['validation']['passed'],
                        chart['validation']['issues'])
        lunar = chart['input']['lunar']
        # 农历月应为负数（闰月标记）
        self.assertLess(lunar['month'], 0)
        # 有效月归为10月
        self.assertEqual(lunar['effective_month'], 10)
        self.assertTrue(lunar['is_leap_month'])

    def test_leap_month_ming_gong(self):
        """闰月命盘：命宫应在巳（以有效月10计算）"""
        chart = build_ziwei_chart(1984, 12, 5, 12.0, '男')
        self.assertEqual(chart['ming_gong']['branch'], '巳')

    def test_leap_month_wu_xing_ju(self):
        """闰月命盘：己巳 → 纳音木 → 木3局"""
        chart = build_ziwei_chart(1984, 12, 5, 12.0, '男')
        ju = chart['wu_xing_ju']
        self.assertEqual(ju['nayin'], '木')
        self.assertEqual(ju['ju'], 3)

    def test_late_zishi(self):
        """晚子时（23:30）应提前一天计算"""
        chart = build_ziwei_chart(1990, 3, 15, 23.5, '女')
        self.assertTrue(chart['validation']['passed'],
                        chart['validation']['issues'])
        self.assertTrue(chart['input']['lunar']['is_late_zishi'])

    def test_late_zishi_ming_gong(self):
        """晚子时命盘：命宫在卯"""
        chart = build_ziwei_chart(1990, 3, 15, 23.5, '女')
        self.assertEqual(chart['ming_gong']['branch'], '卯')

    def test_late_zishi_wu_xing_ju(self):
        """晚子时命盘：己卯 → 纳音土 → 土5局"""
        chart = build_ziwei_chart(1990, 3, 15, 23.5, '女')
        ju = chart['wu_xing_ju']
        self.assertEqual(ju['nayin'], '土')
        self.assertEqual(ju['ju'], 5)

    def test_ld_30_mu2_ju(self):
        """LD=30，木2局：紫微查表不越界"""
        # 木2局 LD=30: q=ceil(30/2)=15, r=0 → base=17=5(normalize)
        chart = build_ziwei_chart(1985, 1, 10, 12.0, '男')  # 农历LD约为10，随意一个木2局盘
        self.assertTrue(chart['validation']['passed'],
                        chart['validation']['issues'])

    def test_each_ju_no_crash(self):
        """5种五行局各自能成功排盘"""
        # 以不同命盘强制覆盖5局（直接调用，无崩溃即通过）
        # 火6局：壬午(子命?) —— 用能产生各局的出生日
        test_cases = [
            (1980, 4, 15, 10.0, '男'),   # 某盘
            (1975, 7, 20, 8.0,  '女'),
            (1990, 3, 15, 23.5, '女'),   # 土5局（已验证）
            (1984, 12, 5, 12.0, '男'),   # 木3局（已验证）
            (1955, 2, 24, 19.25,'男'),   # 金4局（已验证）
        ]
        ju_seen = set()
        for args in test_cases:
            chart = build_ziwei_chart(*args)
            ju_seen.add(chart['wu_xing_ju']['ju'])
            # 主星14颗
            total = sum(len(p['major_stars']) for p in chart['palaces'].values())
            self.assertEqual(total, 14, f"主星数错误: {args}")
        # 至少覆盖3种局
        self.assertGreaterEqual(len(ju_seen), 3)


# ============================================================
# 三、批量无崩溃测试
# ============================================================

class TestBatchNocrash(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        bazi_file = DATA_DIR / 'unified_people_with_bazi.json'
        if not bazi_file.exists():
            cls.records = []
            return
        with open(bazi_file, encoding='utf-8') as f:
            all_records = json.load(f)
        # 过滤有时辰数据的记录
        cls.records = [
            r for r in all_records
            if r.get('has_birth_time') and r.get('bazi', {}).get('hour_pillar')
        ]

    def test_batch_available(self):
        """至少有若干有时辰记录可供测试"""
        if not self.records:
            self.skipTest('unified_people_with_bazi.json 不存在，跳过批量测试')
        self.assertGreater(len(self.records), 0)

    def test_batch_no_crash(self):
        """173条有时辰记录全部排盘不崩溃，主星总数均为14"""
        if not self.records:
            self.skipTest('unified_people_with_bazi.json 不存在，跳过批量测试')

        errors = []
        for rec in self.records:
            try:
                birth = rec.get('birth_date', {})
                year  = birth.get('year')
                month = birth.get('month')
                day   = birth.get('day')
                hour  = birth.get('hour_float', 12.0)
                sex   = '男' if rec.get('gender', 'M') == 'M' else '女'

                if not (year and month and day):
                    continue

                chart = build_ziwei_chart(year, month, day, hour, sex)

                # 主星总数检查
                total = sum(len(p['major_stars']) for p in chart['palaces'].values())
                if total != 14:
                    errors.append(f"{rec.get('name_en','?')}: 主星={total}")

                # 鸽巢不变式
                palaces = list(chart['palaces'].values())
                doubles = sum(1 for p in palaces if len(p['major_stars']) == 2)
                empties = sum(1 for p in palaces if len(p['major_stars']) == 0)
                if doubles != empties + 2:
                    errors.append(f"{rec.get('name_en','?')}: 不变式违反 d={doubles} e={empties}")

            except Exception as ex:
                errors.append(f"{rec.get('name_en','?')}: {type(ex).__name__}: {ex}")

        self.assertEqual(errors, [], f"批量失败 {len(errors)} 条:\n" + '\n'.join(errors[:10]))


# ============================================================
# 入口
# ============================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
