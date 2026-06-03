"""Dataclasses for the eval engine.

These mirror the data contract in docs/SCHEMA.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Case:
    """A single eval case loaded from an evalset."""

    id: str
    category: str
    prompt: str
    expected: str
    judge: str  # exact | contains | regex | json_valid | json_schema | llm
    schema: Optional[Dict[str, Any]] = None  # shape contract for json_schema judge

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Case":
        schema = d.get("schema")
        return cls(
            id=str(d["id"]),
            category=str(d["category"]),
            prompt=str(d["prompt"]),
            expected=str(d.get("expected", "")),
            judge=str(d.get("judge", "contains")),
            schema=schema if isinstance(schema, dict) else None,
        )


@dataclass
class CaseResult:
    """The outcome of running + judging a single case."""

    id: str
    category: str
    prompt: str
    expected: str
    output: str
    passed: bool
    score: float
    latency_ms: int
    judge: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "prompt": self.prompt,
            "expected": self.expected,
            "output": self.output,
            "passed": self.passed,
            "score": round(self.score, 3),
            "latency_ms": self.latency_ms,
            "judge": self.judge,
        }


@dataclass
class CategorySummary:
    total: int = 0
    passed: int = 0
    pass_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "pass_rate": round(self.pass_rate, 3),
        }


@dataclass
class RunSummary:
    total: int = 0
    passed: int = 0
    pass_rate: float = 0.0
    accuracy: float = 0.0
    avg_latency_ms: int = 0
    categories: Dict[str, CategorySummary] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "pass_rate": round(self.pass_rate, 3),
            "accuracy": round(self.accuracy, 3),
            "avg_latency_ms": self.avg_latency_ms,
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
        }


@dataclass
class RunMeta:
    model: str
    evalset: str
    run_id: str
    timestamp: str  # ISO 8601 UTC

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
