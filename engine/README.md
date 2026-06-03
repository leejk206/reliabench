# reliabench (engine)

A small, stdlib-only LLM/agent reliability eval harness. It runs an evalset
of cases against a provider, judges each output, aggregates metrics, and writes
`results.json` + appends to `history.json` per `../docs/SCHEMA.md`.

## Run

```bash
cd engine
python3 -m reliabench run \
  --evalset evalsets/sample.json \
  --model mock \
  --out /tmp/rb_results.json \
  --history /tmp/rb_history.json
```

- `--model mock` uses the deterministic, no-network `MockProvider` (0.75 pass rate on the
  default evalset). It honestly exercises every judge — including emitting valid-but-wrong-shape
  JSON so the `json_schema` judge genuinely fails those `structured_output` cases.
- `claude*` / `gpt*` models lazily use the Anthropic / OpenAI SDKs (optional extras),
  reading `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` from the environment.

Bundled evalsets: `sample.json` (default, 20 cases), `sample-easy.json` / `sample-hard.json`
(difficulty variants for the trend), and `llm-faithfulness.json` (open-ended cases graded by
the `llm` judge — runs only with an API key).

## Test

```bash
cd engine
python3 -m pytest -q
```
