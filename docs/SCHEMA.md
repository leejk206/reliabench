# Data contract — `results.json` / `history.json`

The Python engine writes these; the Next.js dashboard reads them from `dashboard/public/`.
Both sides MUST conform to this contract exactly.

## `results.json` (latest run)

```jsonc
{
  "meta": {
    "model": "mock-echo",            // model/provider id evaluated
    "evalset": "sample-reliability-v1",
    "run_id": "run-0006",
    "timestamp": "2026-06-03T09:00:00Z"  // ISO 8601 UTC
  },
  "summary": {
    "total": 15,
    "passed": 12,
    "pass_rate": 0.80,               // 0..1
    "accuracy": 0.80,                // 0..1 (mean case score)
    "avg_latency_ms": 118,
    "categories": {                  // keyed by category name
      "factual":     { "total": 6, "passed": 5, "pass_rate": 0.833 },
      "format":      { "total": 5, "passed": 4, "pass_rate": 0.800 },
      "consistency": { "total": 4, "passed": 3, "pass_rate": 0.750 }
    }
  },
  "cases": [
    {
      "id": "f1",
      "category": "factual",
      "prompt": "What is the capital of France?",
      "expected": "Paris",
      "output": "Paris",
      "passed": true,
      "score": 1.0,                  // 0..1
      "latency_ms": 110,
      "judge": "contains"            // exact|contains|regex|json_valid|json_schema|llm
    }
  ]
}
```

## `history.json` (one entry appended per run, for time-series)

```jsonc
[
  { "run_id": "run-0001", "timestamp": "2026-05-29T09:00:00Z", "pass_rate": 0.60, "accuracy": 0.61, "avg_latency_ms": 140 },
  { "run_id": "run-0002", "timestamp": "2026-05-30T09:00:00Z", "pass_rate": 0.67, "accuracy": 0.66, "avg_latency_ms": 132 }
]
```

Notes
- `pass_rate`/`accuracy`/`score` are floats in [0,1]. Dashboard renders them as %.
- Categories are dynamic (don't hardcode names).
- `passed` = `score >= pass_threshold` (engine default 1.0 for binary judges, configurable).
