from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "api.py"
SPEC = spec_from_file_location("bazi_pillars_api", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["bazi_pillars_api"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_lichun_boundary_switches_year_and_month_pillar():
    before = MODULE.InterpretRequest(year=2024, month=2, day=4, hour=16, minute=26, gender="女")
    after = MODULE.InterpretRequest(year=2024, month=2, day=4, hour=16, minute=27, gender="女")

    before_pillars = MODULE.build_four_pillars(before)
    after_pillars = MODULE.build_four_pillars(after)

    assert before_pillars["year"] == {"heavenly_stem": "癸", "earthly_branch": "卯"}
    assert before_pillars["month"] == {"heavenly_stem": "乙", "earthly_branch": "丑"}
    assert after_pillars["year"] == {"heavenly_stem": "甲", "earthly_branch": "辰"}
    assert after_pillars["month"] == {"heavenly_stem": "丙", "earthly_branch": "寅"}


def test_jingzhe_boundary_switches_month_pillar():
    before = MODULE.InterpretRequest(year=2024, month=3, day=5, hour=10, minute=22, gender="男")
    after = MODULE.InterpretRequest(year=2024, month=3, day=5, hour=10, minute=23, gender="男")

    before_pillars = MODULE.build_four_pillars(before)
    after_pillars = MODULE.build_four_pillars(after)

    assert before_pillars["month"] == {"heavenly_stem": "丙", "earthly_branch": "寅"}
    assert after_pillars["month"] == {"heavenly_stem": "丁", "earthly_branch": "卯"}


def test_true_solar_time_can_change_day_and_hour_pillar():
    payload = MODULE.InterpretRequest(year=2026, month=3, day=14, hour=0, minute=30, gender="女", city="乌鲁木齐")

    default_pillars = MODULE.build_four_pillars(payload)
    solar_time_info = MODULE._build_solar_time_info(payload)
    corrected_pillars = MODULE.build_four_pillars(payload, solar_time_info=solar_time_info)

    assert solar_time_info["corrected_datetime"] == "2026-03-13T22:10"
    assert default_pillars["day"] != corrected_pillars["day"]
    assert default_pillars["hour"] != corrected_pillars["hour"]
