from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "data_quality_stats.py"
SPEC = spec_from_file_location("data_quality_stats", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["data_quality_stats"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_build_stats_handles_missing_fields():
    people = [
        {"id": "1", "birth_hour": 9, "birth_city": "杭州", "occupation": ["企业家"], "notable_events": [{"year": 1999, "event": "创业"}]},
        {"id": "2", "occupation": []},
        {"id": "3", "has_birth_hour": True, "occupation": ["作家", "演员"]},
    ]

    stats = MODULE.build_stats(people)

    assert stats["total_count"] == 3
    assert stats["with_birth_time"]["count"] == 2
    assert stats["with_birth_city"]["count"] == 1
    assert stats["with_occupation"]["count"] == 2
    assert stats["with_notable_events"]["count"] == 1
    assert stats["occupation_distribution"]["企业家"] == 1
    assert stats["occupation_distribution"]["作家"] == 1
