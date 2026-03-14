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
