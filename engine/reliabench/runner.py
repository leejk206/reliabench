"""Run an evalset against a provider and write results.json + history.json."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .evalset import load_evalset
from .judges import get_judge
from .metrics import aggregate
from .models import CaseResult
from .providers import get_provider


def _next_run_id(history: List[Dict]) -> str:
    """Auto-increment 'run-0007' style id from existing history (start 0001)."""
    max_n = 0
    for entry in history:
        rid = str(entry.get("run_id", ""))
        if rid.startswith("run-"):
            try:
                max_n = max(max_n, int(rid.split("-", 1)[1]))
            except ValueError:
                pass
    return f"run-{max_n + 1:04d}"


def _load_history(history_path: str) -> List[Dict]:
    if history_path and os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (ValueError, OSError):
            pass
    return []


def run(
    evalset_path: str,
    model: str,
    out_path: str,
    history_path: str,
    threshold: float = 1.0,
) -> Dict:
    """Execute the eval and persist results. Returns the results dict."""
    evalset = load_evalset(evalset_path)
    provider = get_provider(model)

    results: List[CaseResult] = []
    for case in evalset.cases:
        if hasattr(provider, "generate_case"):
            output, latency = provider.generate_case(case)
        else:  # pragma: no cover
            output, latency = provider.generate(case.prompt)

        judge_fn = get_judge(case.judge, provider=provider)
        score = float(judge_fn(output, case.expected, case))
        passed = score >= threshold

        results.append(
            CaseResult(
                id=case.id,
                category=case.category,
                prompt=case.prompt,
                expected=case.expected,
                output=output,
                passed=passed,
                score=score,
                latency_ms=int(latency),
                judge=case.judge,
            )
        )

    summary = aggregate(results)

    history = _load_history(history_path)
    run_id = _next_run_id(history)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    results_doc = {
        "meta": {
            "model": getattr(provider, "id", model),
            "evalset": evalset.name,
            "run_id": run_id,
            "timestamp": timestamp,
        },
        "summary": summary,
        "cases": [r.to_dict() for r in results],
    }

    # Write results.json
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results_doc, f, indent=2)
            f.write("\n")

    # Append history entry
    if history_path:
        history.append(
            {
                "run_id": run_id,
                "timestamp": timestamp,
                "pass_rate": summary["pass_rate"],
                "accuracy": summary["accuracy"],
                "avg_latency_ms": summary["avg_latency_ms"],
            }
        )
        os.makedirs(os.path.dirname(os.path.abspath(history_path)), exist_ok=True)
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
            f.write("\n")

    return results_doc
