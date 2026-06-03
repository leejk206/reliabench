from reliabench.metrics import aggregate
from reliabench.models import CaseResult


def _r(id, cat, passed, score, latency):
    return CaseResult(
        id=id, category=cat, prompt="p", expected="e", output="o",
        passed=passed, score=score, latency_ms=latency, judge="contains",
    )


def test_aggregate_known_inputs():
    results = [
        _r("a", "factual", True, 1.0, 100),
        _r("b", "factual", False, 0.0, 200),
        _r("c", "format", True, 1.0, 120),
        _r("d", "format", True, 1.0, 80),
    ]
    s = aggregate(results)
    assert s["total"] == 4
    assert s["passed"] == 3
    assert s["pass_rate"] == 0.75
    assert s["accuracy"] == 0.75
    assert s["avg_latency_ms"] == 125  # (100+200+120+80)/4
    assert s["categories"]["factual"] == {"total": 2, "passed": 1, "pass_rate": 0.5}
    assert s["categories"]["format"] == {"total": 2, "passed": 2, "pass_rate": 1.0}


def test_aggregate_categories_sum_to_total():
    results = [
        _r("a", "x", True, 1.0, 100),
        _r("b", "y", False, 0.0, 100),
        _r("c", "y", True, 1.0, 100),
    ]
    s = aggregate(results)
    assert sum(c["total"] for c in s["categories"].values()) == s["total"]


def test_aggregate_empty():
    s = aggregate([])
    assert s["total"] == 0
    assert s["pass_rate"] == 0.0
    assert s["categories"] == {}
