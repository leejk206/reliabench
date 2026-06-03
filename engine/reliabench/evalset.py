"""Load an evalset JSON file: {"name": str, "cases": [Case...]}."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from .models import Case


@dataclass
class EvalSet:
    name: str
    cases: List[Case]


def load_evalset(path: str) -> EvalSet:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    name = str(data.get("name", "unnamed-evalset"))
    cases = [Case.from_dict(c) for c in data.get("cases", [])]
    if not cases:
        raise ValueError(f"evalset {path!r} has no cases")
    return EvalSet(name=name, cases=cases)
