from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "pdf_generator.py"
SPEC = spec_from_file_location("pdf_generator", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["pdf_generator"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_generate_bazi_report_creates_pdf_bytes(tmp_path):
    interpretation_data = {
        "four_pillars": {
            "year": {"heavenly_stem": "甲", "earthly_branch": "子"},
            "month": {"heavenly_stem": "乙", "earthly_branch": "丑"},
            "day": {"heavenly_stem": "丙", "earthly_branch": "寅"},
            "hour": {"heavenly_stem": "丁", "earthly_branch": "卯"},
        },
        "wuxing_analysis": {
            "wuxing_scores": {"金": 1.2, "木": 2.1, "水": 1.8, "火": 2.6, "土": 1.3},
            "wuxing_percentages": {"金": 13.33, "木": 23.33, "水": 20.0, "火": 28.89, "土": 14.45},
            "day_master": "丙",
            "day_master_element": "火",
            "day_master_strength": "偏强",
            "favorable_elements": ["土", "金"],
            "unfavorable_elements": ["火", "木"],
            "analysis": "日主丙火得月令相生，整体火势偏旺。",
        },
        "dayun": [
            {"start_age": 3, "end_age": 12, "tiangan": "己", "dizhi": "卯"},
            {"start_age": 13, "end_age": 22, "tiangan": "庚", "dizhi": "辰"},
            {"start_age": 23, "end_age": 32, "tiangan": "辛", "dizhi": "巳"},
            {"start_age": 33, "end_age": 42, "tiangan": "壬", "dizhi": "午"},
            {"start_age": 43, "end_age": 52, "tiangan": "癸", "dizhi": "未"},
            {"start_age": 53, "end_age": 62, "tiangan": "甲", "dizhi": "申"},
            {"start_age": 63, "end_age": 72, "tiangan": "乙", "dizhi": "酉"},
            {"start_age": 73, "end_age": 82, "tiangan": "丙", "dizhi": "戌"},
        ],
        "liunian": [
            {"year": 2021, "tiangan": "辛", "dizhi": "丑"},
            {"year": 2022, "tiangan": "壬", "dizhi": "寅"},
            {"year": 2023, "tiangan": "癸", "dizhi": "卯"},
            {"year": 2024, "tiangan": "甲", "dizhi": "辰"},
            {"year": 2025, "tiangan": "乙", "dizhi": "巳"},
            {"year": 2026, "tiangan": "丙", "dizhi": "午"},
            {"year": 2027, "tiangan": "丁", "dizhi": "未"},
            {"year": 2028, "tiangan": "戊", "dizhi": "申"},
            {"year": 2029, "tiangan": "己", "dizhi": "酉"},
            {"year": 2030, "tiangan": "庚", "dizhi": "戌"},
        ],
        "ten_gods_analysis": {
            "比肩": {"interpretation": "比肩代表自主性、边界感与平级竞争意识。"},
            "正印": {"interpretation": "正印强调支持系统、学习吸收和安全感来源。"},
        },
        "psychological_analysis": {
            "荣格原型": "更偏向探索者与照顾者的混合模式。",
            "MBTI倾向": "可能更接近 INFJ / ENFJ 的反思与共情特征。",
        },
    }

    pdf_bytes = MODULE.generate_bazi_report(interpretation_data)

    output_path = tmp_path / "bazi-report.pdf"
    output_path.write_bytes(pdf_bytes)

    assert pdf_bytes.startswith(b"%PDF")
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_generate_bazi_report_writes_sample_output():
    interpretation_data = {
        "input": {
            "birth_year": 1992,
            "birth_month": 11,
            "birth_day": 3,
            "birth_hour": 21,
            "gender": "男",
            "birthplace": "杭州",
        },
        "four_pillars": {
            "year": {"heavenly_stem": "壬", "earthly_branch": "申"},
            "month": {"heavenly_stem": "辛", "earthly_branch": "亥"},
            "day": {"heavenly_stem": "乙", "earthly_branch": "未"},
            "hour": {"heavenly_stem": "丁", "earthly_branch": "亥"},
        },
        "wuxing_analysis": {
            "wuxing_scores": {"金": 1.6, "木": 1.9, "水": 2.8, "火": 1.1, "土": 1.6},
            "wuxing_percentages": {"金": 17.78, "木": 21.11, "水": 31.11, "火": 12.22, "土": 17.78},
            "day_master": "乙",
            "day_master_element": "木",
            "day_master_strength": "偏弱",
            "favorable_elements": ["木", "水"],
            "unfavorable_elements": ["金", "土"],
            "analysis": "日主乙木在亥月得水生扶，木气有根但仍需更多印比助力。",
        },
        "dayun": [
            {"start_age": 4, "end_age": 13, "tiangan": "壬", "dizhi": "子"},
            {"start_age": 14, "end_age": 23, "tiangan": "癸", "dizhi": "丑"},
            {"start_age": 24, "end_age": 33, "tiangan": "甲", "dizhi": "寅"},
            {"start_age": 34, "end_age": 43, "tiangan": "乙", "dizhi": "卯"},
            {"start_age": 44, "end_age": 53, "tiangan": "丙", "dizhi": "辰"},
            {"start_age": 54, "end_age": 63, "tiangan": "丁", "dizhi": "巳"},
            {"start_age": 64, "end_age": 73, "tiangan": "戊", "dizhi": "午"},
            {"start_age": 74, "end_age": 83, "tiangan": "己", "dizhi": "未"},
        ],
        "liunian": [
            {"year": 2021, "tiangan": "辛", "dizhi": "丑"},
            {"year": 2022, "tiangan": "壬", "dizhi": "寅"},
            {"year": 2023, "tiangan": "癸", "dizhi": "卯"},
            {"year": 2024, "tiangan": "甲", "dizhi": "辰"},
            {"year": 2025, "tiangan": "乙", "dizhi": "巳"},
            {"year": 2026, "tiangan": "丙", "dizhi": "午"},
            {"year": 2027, "tiangan": "丁", "dizhi": "未"},
            {"year": 2028, "tiangan": "戊", "dizhi": "申"},
            {"year": 2029, "tiangan": "己", "dizhi": "酉"},
            {"year": 2030, "tiangan": "庚", "dizhi": "戌"},
        ],
        "ten_gods_analysis": {
            "比肩": {"interpretation": "比肩代表自主性与边界意识，在合作关系里强调对等和主动权。"},
            "食神": {"interpretation": "食神体现表达、创造与舒缓压力的能力，也反映审美与生活节奏。"},
            "正印": {"interpretation": "正印强调学习吸收、安全感来源，以及从支持系统中恢复能量。"},
        },
        "psychological_analysis": {
            "荣格原型": "更接近探索者与照顾者的复合倾向，既重视自我生长，也重视关系照料。",
            "MBTI倾向": "可能偏向 INFJ / INFP，兼具内省、价值导向与对他人感受的敏感度。",
            "压力模式": "在高压情境下容易先内化情绪，再通过独处和整理秩序来恢复稳定。",
        },
    }

    pdf_bytes = MODULE.generate_bazi_report(interpretation_data)

    output_dir = Path(__file__).resolve().parents[1] / "test_output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "sample_report.pdf"
    output_path.write_bytes(pdf_bytes)

    assert output_path.exists()
    assert output_path.stat().st_size > 0
