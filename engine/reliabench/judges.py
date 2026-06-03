"""Judge functions that score a model output in [0, 1].

Two kinds of judge exist:

* **Simple judges** — pure functions of ``(output, expected)``:
  ``exact``, ``contains``, ``regex``, ``json_valid``.
* **Case-aware judges** — need the whole :class:`~reliabench.models.Case`
  (for its ``schema``) or a provider (for model-graded grading):
  ``json_schema`` and ``llm``.

The runner always calls a judge as ``judge(output, expected, case)``; simple
judges accept and ignore the trailing ``case`` argument via a thin adapter so
the call site stays uniform. ``passed`` is computed by the caller as
``score >= threshold`` (default 1.0).
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Optional

from .models import Case

# A judge takes (output, expected, case) and returns a float score in [0, 1].
JudgeFn = Callable[[str, str, Optional[Case]], float]


def exact(output: str, expected: str, case: Optional[Case] = None) -> float:
    """1.0 if output equals expected (case-insensitive, trimmed)."""
    return 1.0 if output.strip().lower() == expected.strip().lower() else 0.0


def contains(output: str, expected: str, case: Optional[Case] = None) -> float:
    """1.0 if expected is a substring of output (case-insensitive)."""
    return 1.0 if expected.strip().lower() in output.lower() else 0.0


def regex(output: str, expected: str, case: Optional[Case] = None) -> float:
    """1.0 if the `expected` pattern is found anywhere in output."""
    try:
        return 1.0 if re.search(expected, output) else 0.0
    except re.error:
        return 0.0


def json_valid(output: str, expected: str, case: Optional[Case] = None) -> float:
    """1.0 if output parses as JSON, else 0.0. Well-formedness only.

    Deliberately does NOT check the shape — that is the job of ``json_schema``.
    """
    try:
        json.loads(output)
        return 1.0
    except (ValueError, TypeError):
        return 0.0


def json_schema(output: str, expected: str, case: Optional[Case] = None) -> float:
    """1.0 only if `output` parses as JSON AND matches ``case.schema``.

    A hand-rolled, stdlib-only subset of JSON Schema (no external dep). The
    point is to catch the classic "valid JSON of the wrong shape" failure that
    ``json_valid`` happily passes — e.g. an object where an array of 3 strings
    was demanded.

    Supported shapes::

        {"type": "object", "required": ["k1", "k2", ...]}
        {"type": "array", "items": "number"|"string"}
        {"type": "array", "items": ...,  "length": N}
        {"type": "array", "items": ...,  "min": N}

    ``required``/``items`` are optional. Nesting is not validated (only the
    top-level shape is checked), which is sufficient for the reliability cases
    here and keeps the matcher transparent.
    """
    schema = case.schema if case is not None else None
    if not schema:
        # No contract to check against -> fall back to well-formedness only.
        return json_valid(output, expected, case)
    try:
        data = json.loads(output)
    except (ValueError, TypeError):
        return 0.0
    return 1.0 if _matches_schema(data, schema) else 0.0


def _matches_schema(data: Any, schema: Dict[str, Any]) -> bool:
    expected_type = schema.get("type")

    if expected_type == "object":
        if not isinstance(data, dict):
            return False
        for key in schema.get("required", []):
            if key not in data:
                return False
        return True

    if expected_type == "array":
        if not isinstance(data, list):
            return False
        if "length" in schema and len(data) != int(schema["length"]):
            return False
        if "min" in schema and len(data) < int(schema["min"]):
            return False
        items = schema.get("items")
        if items is not None:
            for el in data:
                if not _item_matches(el, items):
                    return False
        return True

    if expected_type == "number":
        return isinstance(data, (int, float)) and not isinstance(data, bool)
    if expected_type == "string":
        return isinstance(data, str)

    # Unknown/absent type -> any successfully-parsed JSON is acceptable.
    return True


def _item_matches(el: Any, items: Any) -> bool:
    if items == "number":
        return isinstance(el, (int, float)) and not isinstance(el, bool)
    if items == "string":
        return isinstance(el, str)
    if isinstance(items, dict):
        return _matches_schema(el, items)
    return True


# --- LLM-as-judge --------------------------------------------------------------

_RUBRIC = (
    "You are a strict grader for an AI reliability eval. Decide whether the "
    "CANDIDATE answer satisfies the CRITERION for the given TASK.\n\n"
    "Grade only on the criterion. Be conservative: if the answer is "
    "unfaithful, adds unsupported claims, or ignores the task, it FAILS.\n\n"
    "TASK:\n{prompt}\n\n"
    "CRITERION (what a passing answer must satisfy):\n{expected}\n\n"
    "CANDIDATE ANSWER:\n{output}\n\n"
    "Reply in EXACTLY this format and nothing else:\n"
    "VERDICT: PASS or FAIL\n"
    "REASON: <one sentence>\n"
)


def _parse_verdict(text: str) -> float:
    """Robustly extract PASS/FAIL from a model grading reply."""
    if not text:
        return 0.0
    m = re.search(r"VERDICT\s*:\s*(PASS|FAIL)", text, re.IGNORECASE)
    if m:
        return 1.0 if m.group(1).upper() == "PASS" else 0.0
    # Fallback: look for a standalone PASS/FAIL token, FAIL wins ties.
    upper = text.upper()
    has_fail = re.search(r"\bFAIL\b", upper) is not None
    has_pass = re.search(r"\bPASS\b", upper) is not None
    if has_fail:
        return 0.0
    if has_pass:
        return 1.0
    return 0.0


def make_llm_judge(provider: Optional[object] = None) -> JudgeFn:
    """Build a model-graded (LLM-as-judge) function.

    With a real `provider` the candidate answer is graded against a rubric and
    the PASS/FAIL verdict is parsed. With **no** provider (offline / no API key)
    it degrades to the ``contains`` heuristic so the harness still runs — but
    this is explicitly a *fallback*, not real model grading, and the default
    offline evalset intentionally contains zero ``llm`` cases.
    """

    def llm(output: str, expected: str, case: Optional[Case] = None) -> float:
        if provider is None:
            # No provider/key available -> degrade to a substring heuristic.
            return contains(output, expected, case)
        prompt = _RUBRIC.format(
            prompt=(case.prompt if case is not None else ""),
            expected=expected,
            output=output,
        )
        try:
            verdict, _latency = provider.generate(prompt)
        except Exception:
            return contains(output, expected, case)
        return _parse_verdict(verdict)

    return llm


# Registry of stdlib-only judges. `llm` is registered with the offline fallback;
# callers that have a provider override it via get_judge(name, provider=...).
REGISTRY: Dict[str, JudgeFn] = {
    "exact": exact,
    "contains": contains,
    "regex": regex,
    "json_valid": json_valid,
    "json_schema": json_schema,
    "llm": make_llm_judge(None),
}


def get_judge(name: str, provider: Optional[object] = None) -> JudgeFn:
    """Return the judge fn for `name`. `llm` is built with the given provider."""
    if name == "llm":
        return make_llm_judge(provider)
    if name not in REGISTRY:
        raise ValueError(f"unknown judge: {name!r} (have: {sorted(REGISTRY)})")
    return REGISTRY[name]
