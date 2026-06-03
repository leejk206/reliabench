# reliabench

**A reliability monitor for LLM & agent outputs — tracks whether a model regresses run over run.**

**[▶ Live demo](https://reliabench.vercel.app)** · the demo data is a real, blind Claude run (no API key — via Claude Code).

![reliabench dashboard](docs/dashboard.png)

reliabench runs an evaluation set against a model on every run, scores each response
with deterministic judges (exact / contains / regex / JSON-validity / **JSON-schema**)
plus an optional model-graded **LLM-as-judge**, and renders the resulting reliability
signal — pass rate, accuracy, per-category breakdown, latency, and **trend across runs** —
in a monitoring dashboard. It also doubles as a plain eval harness.

> Built to answer the question teams keep asking: *"Is our AI actually staying reliable,
> run over run — and where is it starting to break?"*

## Why

Shipping LLM features is easy; **knowing whether they keep doing what they should** is not.
reliabench turns "it seems fine" into measured, visualized, regression-tracked numbers —
the same way you'd monitor a service's error rate. Each run appends one point to
`history.json`, so a drop in pass rate between runs is visible immediately.

## Architecture

```
reliabench/
├── engine/                 # Python eval harness (stdlib-only core; optional LLM providers)
│   ├── reliabench/         # loader, judges, providers, metrics, CLI
│   ├── evalsets/           # evaluation sets (JSON)
│   └── tests/              # pytest
└── dashboard/              # Next.js (App Router, TS) + Recharts
    └── public/             # results.json + history.json (engine output, read by the UI)
```

The two sides talk through a single JSON contract: [`docs/SCHEMA.md`](docs/SCHEMA.md).

## Judges

| judge         | passes when…                                                                 |
|---------------|------------------------------------------------------------------------------|
| `exact`       | output equals `expected` (trimmed, case-insensitive)                         |
| `contains`    | `expected` is a substring of output                                          |
| `regex`       | the `expected` pattern matches output (e.g. `^(YES|NO)$`, ISO date, phone)   |
| `json_valid`  | output is well-formed JSON (shape **not** checked)                           |
| `json_schema` | output parses **and matches the case's `schema`** — the demanded shape       |
| `llm`         | a grader model returns `VERDICT: PASS` for the case's rubric (needs a key)   |

`json_schema` is the key reliability check: a prompt that asks for "a JSON array of exactly
3 strings" **fails** if the model returns a valid JSON *object* instead. The `schema` field
supports `{"type":"object","required":[...]}` and `{"type":"array","items":"number"|"string","length":N|"min":N}`.

**LLM-as-judge** (`llm`) is model-graded judging: it sends the task + a PASS/FAIL rubric to a
grader model and parses the verdict. It **runs only when an API key is set** — it is not
demonstrated by the committed offline data. The open-ended faithfulness cases that genuinely
need it live in [`engine/evalsets/llm-faithfulness.json`](engine/evalsets/llm-faithfulness.json),
not in the default evalset.

## Quickstart (offline, no API key)

```bash
# Run the evaluation with the deterministic mock model
cd engine
python3 -m reliabench run --evalset evalsets/sample.json --model mock \
  --out ../dashboard/public/results.json --history ../dashboard/public/history.json

# View the dashboard
cd ../dashboard
npm install && npm run dev   # http://localhost:3000
```

## Run it against a real model

### No API key — use your Claude Code subscription (recommended)

If you have [Claude Code](https://claude.com/claude-code) installed and logged in, the
`claude-code` provider shells out to `claude -p` and evaluates **real Claude** with **no API
key**. Each case runs in an isolated temp dir, so the model can't read the evalset (answer key)
— the eval stays blind.

```bash
cd engine
python3 -m reliabench run --model claude-code \
  --evalset evalsets/sample.json \
  --out ../dashboard/public/results.json \
  --history ../dashboard/public/history.json
```

### With an API key (Anthropic / OpenAI)

```bash
ANTHROPIC_API_KEY=... python3 -m reliabench run --model claude-sonnet-4-6 \
  --evalset engine/evalsets/sample.json \
  --out dashboard/public/results.json --history dashboard/public/history.json

# Faithfulness set graded by the LLM-as-judge (needs a key):
ANTHROPIC_API_KEY=... python3 -m reliabench run --model claude-sonnet-4-6 \
  --evalset engine/evalsets/llm-faithfulness.json \
  --out dashboard/public/results.json --history dashboard/public/history.json
```

## Demo data — a real Claude run

The committed `dashboard/public/results.json` and `history.json` are **real**, from two blind
runs of Claude (via the keyless `claude-code` provider) over the default evalset. They show
genuine reliability findings — e.g. Claude wraps JSON in ```` ```json ```` fences or adds prose
when asked to "return ONLY JSON," so several `structured_output` / `format_contract` cases
fail `json_schema` / `regex` — and real per-call latency (~9 s). Pass rate varies run over run
(0.80 → 0.85), which is exactly the signal the trend chart exists to surface.

Re-run either command above to append your own points. The deterministic `mock` provider
remains available for fully offline, reproducible runs (see Quickstart).

## Screenshots

![reliabench dashboard — KPIs, reliability trend, per-category pass rate, and the cases table showing real Claude failures](docs/dashboard.png)

Live: **https://reliabench.vercel.app**

## Tech

Python (eval engine, stdlib core) · TypeScript · Next.js (App Router) · Recharts (data viz).

## Status

MVP. Deterministic mock + four bundled evalsets (default, easy, hard, llm-faithfulness)
work end-to-end; the Anthropic/OpenAI providers plug in via the provider interface and run
when a key is present.
