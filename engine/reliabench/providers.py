"""Providers implement `generate(prompt) -> (output, latency_ms)`.

The core MockProvider is deterministic and stdlib-only. Anthropic / OpenAI
providers lazy-import their SDKs and read keys from the environment; they are
never imported unless explicitly selected via `get_provider`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

from .models import Case


def _wrong_for(case: Case) -> bool:
    """Deterministic ~20% wrong subset: wrong iff sum(ord) % 5 == 0."""
    return sum(ord(c) for c in case.id) % 5 == 0


def _latency_for(case: Case) -> int:
    """Deterministic simulated latency in ms (~96..145)."""
    h = sum(ord(c) * (i + 1) for i, c in enumerate(case.id))
    return 96 + (h % 50)


class MockProvider:
    """Deterministic, no-network provider for reproducible runs."""

    id = "mock-echo"

    def generate_case(self, case: Case) -> Tuple[str, int]:
        """Produce an output for a full Case (needs judge + expected)."""
        latency = _latency_for(case)
        wrong = _wrong_for(case)

        if case.judge == "json_schema":
            # Honor the shape contract: produce schema-matching JSON when
            # "correct", and VALID-but-WRONG-SHAPE JSON when "wrong" so the
            # json_schema judge genuinely fails it (json_valid would pass both).
            output = (
                _schema_violator(case.schema) if wrong
                else _schema_satisfier(case.schema)
            )
        elif case.judge == "json_valid":
            output = '{ broken' if wrong else '{"status": "ok"}'
        elif case.judge == "regex":
            if wrong:
                output = "no-match-here"
            else:
                output = _regex_satisfier(case.expected)
        else:
            # exact / contains / llm: echo expected when correct.
            output = _mangle(case.expected) if wrong else case.expected

        return output, latency

    def generate(self, prompt: str) -> Tuple[str, int]:
        """Bare prompt interface (used by the llm-judge fallback path)."""
        # Deterministic, content-free echo; not used for case scoring.
        return prompt, 100


def _mangle(expected: str) -> str:
    """Return a deliberately wrong answer that does NOT contain `expected`.

    Must fail both `exact` and `contains` judges, so we cannot simply wrap the
    expected value (that would still satisfy `contains`).
    """
    if not expected:
        return "WRONG"
    candidate = "WRONG-" + expected[::-1]
    # Guard against palindromes / single chars where reversal still contains
    # the expected substring under a case-insensitive `contains` check.
    if expected.strip().lower() in candidate.lower():
        return "DELIBERATELY-INCORRECT"
    return candidate


def _schema_satisfier(schema: Dict[str, Any] | None) -> str:
    """Produce valid JSON that MATCHES the given hand-rolled schema."""
    return json.dumps(_build_value(schema, satisfy=True))


def _schema_violator(schema: Dict[str, Any] | None) -> str:
    """Produce valid JSON that VIOLATES the shape (but still parses).

    Strategy: emit a value of a deliberately different JSON type than the
    schema demands (object<->array), or drop a required key, so json_valid
    passes while json_schema fails.
    """
    return json.dumps(_build_value(schema, satisfy=False))


def _build_value(schema: Dict[str, Any] | None, satisfy: bool) -> Any:
    if not schema:
        return {"status": "ok"} if satisfy else {"status": "ok"}

    t = schema.get("type")
    if t == "object":
        required = list(schema.get("required", []))
        if satisfy:
            return {k: _placeholder_for(k) for k in required} or {"ok": True}
        # Wrong shape: an array instead of the required object.
        return ["unexpected", "array", "shape"]

    if t == "array":
        items = schema.get("items")
        length = schema.get("length")
        n = int(length) if length is not None else int(schema.get("min", 3))
        if satisfy:
            return [_item_value(items, i) for i in range(n)]
        # Wrong shape: an object instead of the required array.
        return {"error": "expected an array but got an object"}

    if t == "number":
        return 0.5 if satisfy else "not-a-number"
    if t == "string":
        return "value" if satisfy else 123

    return {"status": "ok"}


def _placeholder_for(key: str) -> Any:
    """Best-effort realistic value for a known key, else a generic string."""
    k = key.lower()
    if k == "sentiment":
        return "positive"
    if k == "score":
        return 0.92
    if k in {"confidence", "rating"}:
        return 0.5
    return "value"


def _item_value(items: Any, i: int) -> Any:
    if items == "number":
        return i
    if items == "string":
        return f"tag{i + 1}"
    return f"item{i + 1}"


def _regex_satisfier(pattern: str) -> str:
    """Return a literal string that matches common simple regex patterns.

    Stdlib-only; handles the patterns used in the sample evalset
    (e.g. ``\\d{3}-\\d{3}-\\d{4}``) and falls back to a generic guess.
    """
    import re

    # Known patterns used by the bundled evalsets -> canonical literal answers.
    known = {
        r"\d{3}-\d{3}-\d{4}": "415-555-2671",
        r"^\d{4}-\d{2}-\d{2}$": "2026-06-03",
        r"^(YES|NO)$": "YES",
        r"(?i)(can'?t|cannot|unable|won'?t|will not)": (
            "I'm sorry, but I can't help with that request."
        ),
    }
    if pattern in known:
        return known[pattern]

    # Generic best-effort: replace common tokens with literals.
    out = pattern
    out = re.sub(r"\\d\{(\d+)\}", lambda m: "1" * int(m.group(1)), out)
    out = out.replace(r"\d", "1").replace(r"\w", "x").replace(r"\s", " ")
    out = out.replace("^", "").replace("$", "")
    # If still regex-y, just try matching against a digit-rich sample.
    try:
        if re.search(pattern, out):
            return out
    except re.error:
        pass
    return out


class AnthropicProvider:
    """Anthropic provider. SDK is imported lazily in __init__."""

    def __init__(self, model: str):
        try:
            import anthropic  # type: ignore
        except ImportError as e:  # pragma: no cover - optional dep
            raise RuntimeError(
                "anthropic SDK not installed. Install with: pip install 'reliabench[anthropic]'"
            ) from e
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in the environment.")
        self.id = model
        self.model = model
        self._client = anthropic.Anthropic(api_key=key)

    def generate(self, prompt: str) -> Tuple[str, int]:  # pragma: no cover - network
        import time

        start = time.perf_counter()
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        latency = int((time.perf_counter() - start) * 1000)
        text = "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        )
        return text, latency

    def generate_case(self, case: Case) -> Tuple[str, int]:  # pragma: no cover
        return self.generate(case.prompt)


class OpenAIProvider:
    """OpenAI provider. SDK is imported lazily in __init__."""

    def __init__(self, model: str):
        try:
            import openai  # type: ignore
        except ImportError as e:  # pragma: no cover - optional dep
            raise RuntimeError(
                "openai SDK not installed. Install with: pip install 'reliabench[openai]'"
            ) from e
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
        self.id = model
        self.model = model
        self._client = openai.OpenAI(api_key=key)

    def generate(self, prompt: str) -> Tuple[str, int]:  # pragma: no cover - network
        import time

        start = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        latency = int((time.perf_counter() - start) * 1000)
        return resp.choices[0].message.content or "", latency

    def generate_case(self, case: Case) -> Tuple[str, int]:  # pragma: no cover
        return self.generate(case.prompt)


class ClaudeCodeProvider:
    """Real Claude via the local Claude Code CLI (``claude -p``).

    No API key required — it uses the machine's existing Claude Code
    subscription auth. One CLI invocation per case. This makes a genuine
    model run reproducible by anyone who has Claude Code installed.
    """

    def __init__(self, model: str = "claude-code", timeout: float = 120.0):
        import shutil
        import tempfile

        if shutil.which("claude") is None:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "claude CLI not found. Install Claude Code, or use --model mock."
            )
        self.id = model
        self.timeout = timeout
        # Run in an isolated empty dir so the model under test can't read the
        # evalset (answer key) from the working tree — keeps the eval blind.
        self._cwd = tempfile.mkdtemp(prefix="reliabench-cc-")

    def generate(self, prompt: str) -> Tuple[str, int]:
        import subprocess
        import time

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self._cwd,
            )
            out = (proc.stdout or "").strip()
            if proc.returncode != 0 and not out:
                out = "[reliabench: claude CLI error] " + (proc.stderr or "").strip()
        except subprocess.TimeoutExpired:
            out = "[reliabench: claude CLI timed out]"
        latency = int((time.perf_counter() - start) * 1000)
        return out, latency

    def generate_case(self, case: Case) -> Tuple[str, int]:
        return self.generate(case.prompt)


def get_provider(model: str):
    """Factory: map a model id to a provider instance."""
    if model in {"mock", "mock-echo"}:
        return MockProvider()
    # Keyless real model via the Claude Code CLI (subscription auth).
    if model in {"claude-code", "cc"}:
        return ClaudeCodeProvider(model="claude-code")
    if model.startswith("claude"):
        return AnthropicProvider(model)
    if model.startswith("gpt"):
        return OpenAIProvider(model)
    raise ValueError(
        f"unknown model {model!r}: use 'mock', 'claude-code', a 'claude*' "
        f"or a 'gpt*' model id."
    )
