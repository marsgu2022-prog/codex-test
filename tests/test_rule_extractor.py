from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "rule_extractor.py"
SPEC = spec_from_file_location("rule_extractor", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["rule_extractor"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_extract_rules_groups_by_day_master_and_confidence():
    readings = [
        {
            "name_en": "A",
            "birth_date": "1990-01-01",
            "bazi_pillars": {"month": "乙酉"},
            "reading": {
                "day_master": "甲",
                "pattern": "正官格",
                "pattern_reasoning": "月令透官。",
                "useful_god": "火、土",
                "useful_god_reasoning": "身弱喜印比。",
                "career_tendency": ["管理", "法律"],
                "career_reasoning": "官格重秩序。",
                "personality_traits": ["有原则"],
                "strength_reasoning": "甲木弱。",
                "confidence": 0.9,
            },
        },
        {
            "name_en": "B",
            "birth_date": "1991-01-01",
            "bazi_pillars": {"month": "丁酉"},
            "reading": {
                "day_master": "甲",
                "pattern": "正官格",
                "pattern_reasoning": "月令透官。",
                "useful_god": "火、土",
                "useful_god_reasoning": "身弱喜印比。",
                "career_tendency": ["管理"],
                "career_reasoning": "官格重秩序。",
                "personality_traits": ["有原则"],
                "strength_reasoning": "甲木弱。",
                "confidence": 0.85,
            },
        },
        {
            "name_en": "C",
            "birth_date": "1992-01-01",
            "bazi_pillars": {"month": "丁酉"},
            "reading": {
                "day_master": "甲",
                "pattern": "正官格",
                "pattern_reasoning": "低置信样本。",
                "useful_god": "火",
                "career_tendency": ["管理"],
                "personality_traits": ["谨慎"],
                "confidence": 0.5,
            },
        },
    ]

    stats = MODULE.extract_rules(readings, 0.8)

    assert stats["high_confidence_readings"] == 2
    assert "甲木日主" in stats["day_masters"]
    payload = stats["day_masters"]["甲木日主"]
    assert payload["sample_count"] == 2
    assert payload["patterns"][0]["text"] == "甲木生于酉月，多见正官格"
    assert payload["patterns"][0]["count"] == 2
    assert payload["career_tendencies"][0]["text"] == "适合管理方向"


def test_render_markdown_and_main_write_files(tmp_path):
    input_path = tmp_path / "bazi_readings.json"
    output_md = tmp_path / "auto_rules.md"
    output_stats = tmp_path / "auto_rules_stats.json"
    payload = [
        {
            "name_en": "A",
            "birth_date": "1990-01-01",
            "bazi_pillars": {"month": "乙酉"},
            "reading": {
                "day_master": "甲",
                "pattern": "正官格",
                "pattern_reasoning": "月令透官。",
                "useful_god": "火、土",
                "useful_god_reasoning": "身弱喜印比。",
                "career_tendency": ["管理"],
                "career_reasoning": "官格重秩序。",
                "personality_traits": ["有原则"],
                "strength_reasoning": "甲木弱。",
                "confidence": 0.85,
            },
        }
    ]
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    old_argv = sys.argv
    sys.argv = [
        "rule_extractor.py",
        "--input",
        str(input_path),
        "--output-md",
        str(output_md),
        "--output-stats",
        str(output_stats),
    ]
    try:
        MODULE.main()
    finally:
        sys.argv = old_argv

    md_text = output_md.read_text(encoding="utf-8")
    stats = json.loads(output_stats.read_text(encoding="utf-8"))
    assert "## 甲木日主" in md_text
    assert "适合管理方向" in md_text
    assert stats["day_masters"]["甲木日主"]["sample_count"] == 1
