from reliabench import judges
from reliabench.models import Case


def _case(judge="contains", schema=None, prompt="?", expected=""):
    return Case(id="t1", category="c", prompt=prompt, expected=expected, judge=judge, schema=schema)


def test_exact():
    assert judges.exact("Paris", " paris ") == 1.0
    assert judges.exact("Paris", "Lyon") == 0.0


def test_contains():
    assert judges.contains("The capital is Paris.", "paris") == 1.0
    assert judges.contains("Lyon", "Paris") == 0.0


def test_regex():
    assert judges.regex("call 415-555-2671", r"\d{3}-\d{3}-\d{4}") == 1.0
    assert judges.regex("no digits here", r"\d{3}-\d{3}-\d{4}") == 0.0
    # invalid pattern -> 0.0, no crash
    assert judges.regex("anything", r"[") == 0.0


def test_json_valid():
    assert judges.json_valid('{"status": "ok"}', "valid json") == 1.0
    assert judges.json_valid("{ broken", "valid json") == 0.0


def test_json_schema_object_pass_and_fail():
    schema = {"type": "object", "required": ["sentiment", "score"]}
    case = _case(judge="json_schema", schema=schema)
    # Shape matches -> pass
    assert judges.json_schema('{"sentiment": "positive", "score": 0.9}', "", case) == 1.0
    # Valid JSON, wrong shape (missing required key) -> fail
    assert judges.json_schema('{"sentiment": "positive"}', "", case) == 0.0
    # Valid JSON, wrong type (array not object) -> fail
    assert judges.json_schema('["a", "b"]', "", case) == 0.0


def test_json_schema_array_length_and_items():
    schema = {"type": "array", "items": "string", "length": 3}
    case = _case(judge="json_schema", schema=schema)
    # Exactly 3 strings -> pass
    assert judges.json_schema('["a", "b", "c"]', "", case) == 1.0
    # Wrong length -> fail
    assert judges.json_schema('["a", "b"]', "", case) == 0.0
    # Wrong item type -> fail
    assert judges.json_schema('[1, 2, 3]', "", case) == 0.0
    # Valid JSON object instead of array -> fail (the classic json_valid trap)
    assert judges.json_schema('{"status": "ok"}', "", case) == 0.0


def test_json_schema_array_min_and_number_items():
    schema = {"type": "array", "items": "number", "min": 2}
    case = _case(judge="json_schema", schema=schema)
    assert judges.json_schema('[1, 2, 3]', "", case) == 1.0
    assert judges.json_schema('[1]', "", case) == 0.0
    # booleans are not numbers
    assert judges.json_schema('[true, false]', "", case) == 0.0


def test_json_schema_unparseable_fails():
    case = _case(judge="json_schema", schema={"type": "object", "required": ["a"]})
    assert judges.json_schema("{ not json", "", case) == 0.0


def test_json_schema_no_schema_falls_back_to_well_formedness():
    case = _case(judge="json_schema", schema=None)
    assert judges.json_schema('{"x": 1}', "", case) == 1.0
    assert judges.json_schema("{ broken", "", case) == 0.0


def test_llm_fallback_to_contains():
    # No provider -> falls back to contains.
    llm = judges.get_judge("llm", provider=None)
    assert llm("contains Paris", "paris", None) == 1.0
    assert llm("nope", "paris", None) == 0.0


def test_llm_with_provider_parses_verdict():
    class PassProvider:
        def generate(self, prompt):
            return "VERDICT: PASS\nREASON: faithful summary", 5

    class FailProvider:
        def generate(self, prompt):
            return "VERDICT: FAIL\nREASON: hallucinated a date", 5

    case = _case(judge="llm", prompt="Summarize", expected="be faithful")
    assert judges.get_judge("llm", provider=PassProvider())("anything", "be faithful", case) == 1.0
    assert judges.get_judge("llm", provider=FailProvider())("anything", "be faithful", case) == 0.0


def test_parse_verdict_robustness():
    assert judges._parse_verdict("VERDICT: PASS") == 1.0
    assert judges._parse_verdict("verdict: fail\nreason: x") == 0.0
    # No explicit VERDICT line; FAIL token wins.
    assert judges._parse_verdict("This should PASS but actually FAIL") == 0.0
    assert judges._parse_verdict("Looks good, PASS") == 1.0
    assert judges._parse_verdict("") == 0.0


def test_get_judge_unknown():
    import pytest

    with pytest.raises(ValueError):
        judges.get_judge("nope")


def test_json_schema_registered():
    assert "json_schema" in judges.REGISTRY
