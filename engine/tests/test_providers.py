import json

from reliabench.models import Case
from reliabench.providers import MockProvider, get_provider, _wrong_for


def test_mock_determinism():
    p = MockProvider()
    case = Case(id="if1", category="instruction_following", prompt="?", expected="^(YES|NO)$", judge="regex")
    out1, lat1 = p.generate_case(case)
    out2, lat2 = p.generate_case(case)
    assert out1 == out2
    assert lat1 == lat2


def test_mock_wrong_subset_rule():
    p = MockProvider()
    # if5: sum(ord) % 5 == 0 -> wrong -> output does not match YES/NO contract
    assert _wrong_for(Case(id="if5", category="x", prompt="?", expected="^(YES|NO)$", judge="regex"))
    out, _ = p.generate_case(Case(id="if5", category="x", prompt="?", expected="^(YES|NO)$", judge="regex"))
    import re
    assert re.search(r"^(YES|NO)$", out) is None
    # if2: not wrong -> echoes a matching answer
    assert not _wrong_for(Case(id="if2", category="x", prompt="?", expected="HELLO", judge="exact"))
    out, _ = p.generate_case(Case(id="if2", category="x", prompt="?", expected="HELLO", judge="exact"))
    assert out == "HELLO"


def test_mock_json_schema_correct_matches_shape():
    p = MockProvider()
    # so2 is NOT in the wrong subset -> should emit schema-matching object.
    schema = {"type": "object", "required": ["sentiment", "score"]}
    case = Case(id="so2", category="structured_output", prompt="?", expected="", judge="json_schema", schema=schema)
    assert not _wrong_for(case)
    out, _ = p.generate_case(case)
    data = json.loads(out)  # valid JSON
    assert isinstance(data, dict)
    assert "sentiment" in data and "score" in data


def test_mock_json_schema_wrong_is_valid_json_but_wrong_shape():
    p = MockProvider()
    # so1 IS in the wrong subset -> array schema, so violator emits an OBJECT.
    schema = {"type": "array", "items": "string", "length": 3}
    case = Case(id="so1", category="structured_output", prompt="?", expected="", judge="json_schema", schema=schema)
    assert _wrong_for(case)
    out, _ = p.generate_case(case)
    data = json.loads(out)  # still parses as valid JSON
    assert not isinstance(data, list)  # wrong shape: not the demanded array


def test_get_provider_factory():
    assert isinstance(get_provider("mock"), MockProvider)
    assert isinstance(get_provider("mock-echo"), MockProvider)
    import pytest

    with pytest.raises(ValueError):
        get_provider("llama-3")
