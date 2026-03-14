from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai_interpreter import AIInterpreter, STYLE_GUIDE, TEN_GOD_ARCHETYPES, post_interpret


def sample_payload():
    return {
        "day_master": "甲",
        "dominant_gods": ["比肩", "正印"],
        "ten_gods": {"比肩": 9, "正印": 8, "七杀": 4},
    }


def test_bilingual_output():
    result = post_interpret({**sample_payload(), "lang": "both"})
    assert result["lang"] == "both"
    assert "zh" in result["narrative"]
    assert "en" in result["narrative"]
    assert "你更像" in result["narrative"]["zh"]
    assert "You're a natural starter" in result["narrative"]["en"]


def test_zh_output():
    result = post_interpret({**sample_payload(), "lang": "zh"})
    assert result["lang"] == "zh"
    assert "你更像" in result["narrative"]
    assert "You're a natural starter" not in result["narrative"]
    assert "Your chart highlights a strong drive toward self-direction" not in result["narrative"]


def test_style_guide_in_prompt():
    interpreter = AIInterpreter()
    prompt = interpreter._build_prompt(sample_payload(), lang="both")
    assert STYLE_GUIDE in prompt
    assert "STYLE RULES:" in prompt


def test_new_archetype_fields():
    required_fields = {"attachment", "shadow", "growth"}
    for archetype in TEN_GOD_ARCHETYPES.values():
        assert required_fields.issubset(archetype.keys())
