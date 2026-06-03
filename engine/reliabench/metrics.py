"""Aggregate a list of CaseResults into a summary dict per docs/SCHEMA.md."""

from __future__ import annotations

from typing import Dict, List

from .models import CaseResult


def aggregate(results: List[CaseResult]) -> Dict:
    """Build the `summary` block. All floats rounded to 3 dp."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    pass_rate = (passed / total) if total else 0.0
    accuracy = (sum(r.score for r in results) / total) if total else 0.0
    avg_latency = (sum(r.latency_ms for r in results) / total) if total else 0.0

    categories: Dict[str, Dict] = {}
    for r in results:
        c = categories.setdefault(r.category, {"total": 0, "passed": 0})
        c["total"] += 1
        if r.passed:
            c["passed"] += 1
    for cat in categories.values():
        cat["pass_rate"] = round(cat["passed"] / cat["total"], 3) if cat["total"] else 0.0

    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(pass_rate, 3),
        "accuracy": round(accuracy, 3),
        "avg_latency_ms": round(avg_latency),
        "categories": categories,
    }
