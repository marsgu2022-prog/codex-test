from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from random import Random
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DAY_PILLAR_INDEX_PATH = BASE_DIR / "data" / "day_pillar_index.json"


@lru_cache(maxsize=1)
def load_day_pillar_index() -> dict[str, list[dict[str, Any]]]:
    return json.loads(DAY_PILLAR_INDEX_PATH.read_text(encoding="utf-8"))


def get_famous_matches(day_pillar: str, limit: int = 10) -> list[dict[str, Any]]:
    matches = list(load_day_pillar_index().get(day_pillar, []))
    Random(day_pillar).shuffle(matches)
    return matches[:limit]
