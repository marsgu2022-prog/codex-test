from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "bazichart-engine" / "scripts" / "generate_metadata_layers.py"
SPEC = spec_from_file_location("generate_metadata_layers", MODULE_PATH)
MODULE = module_from_spec(SPEC)
sys.modules["generate_metadata_layers"] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_build_rule_fragments_reaches_target_volume():
    fragments = MODULE.build_rule_fragments()

    assert len(fragments) >= 100
    assert fragments[0]["rule_id"].startswith("RF")
    assert fragments[0]["condition"]


def test_build_case_event_links_uses_timed_people_only():
    people = [
        {
            "id": "p1",
            "has_birth_hour": True,
            "notable_events": [{"year": 2007, "event": "发布iPhone"}],
        },
        {
            "id": "p2",
            "has_birth_hour": False,
            "notable_events": [{"year": 2008, "event": "结婚"}],
        },
    ]

    links = MODULE.build_case_event_links(people)

    assert len(links) == 1
    assert links[0]["person_id"] == "p1"
    assert links[0]["event_type"] == "career_peak"
