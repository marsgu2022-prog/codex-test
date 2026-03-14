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
