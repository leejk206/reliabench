import json
import os

from reliabench.runner import run

EVALSET = os.path.join(os.path.dirname(__file__), "..", "evalsets", "sample.json")


def test_full_run_conforms_to_schema(tmp_path):
    out = tmp_path / "results.json"
    hist = tmp_path / "history.json"

    doc = run(str(EVALSET), "mock", str(out), str(hist))

    # results.json written and re-loadable
    assert out.exists()
    with open(out) as f:
        loaded = json.load(f)
    assert loaded == doc

    # meta keys
    for k in ("model", "evalset", "run_id", "timestamp"):
        assert k in loaded["meta"]
    assert loaded["meta"]["model"] == "mock-echo"
    assert loaded["meta"]["evalset"] == "sample-reliability-v1"
    assert loaded["meta"]["run_id"] == "run-0001"
    assert loaded["meta"]["timestamp"].endswith("Z")

    # summary keys + ranges
    s = loaded["summary"]
    for k in ("total", "passed", "pass_rate", "accuracy", "avg_latency_ms", "categories"):
        assert k in s
    assert 0.0 <= s["pass_rate"] <= 1.0
    assert 0.0 <= s["accuracy"] <= 1.0
    assert s["total"] == 20

    # categories sum to total
    assert sum(c["total"] for c in s["categories"].values()) == s["total"]
    assert sum(c["passed"] for c in s["categories"].values()) == s["passed"]

    # deterministic mock: 5 of 20 in the wrong subset -> 15 pass, 0.75
    assert s["passed"] == 15
    assert s["pass_rate"] == 0.75

    # every case has required fields
    for c in loaded["cases"]:
        for k in ("id", "category", "prompt", "expected", "output", "passed", "score", "latency_ms", "judge"):
            assert k in c
        assert 0.0 <= c["score"] <= 1.0


def test_json_schema_case_fails_wrong_shape(tmp_path):
    """The json_schema judge must FAIL valid-but-wrong-shape JSON."""
    out = tmp_path / "results.json"
    hist = tmp_path / "history.json"
    doc = run(str(EVALSET), "mock", str(out), str(hist))

    by_id = {c["id"]: c for c in doc["cases"]}
    # so1: array schema, in wrong subset -> mock emits a VALID object -> must fail.
    so1 = by_id["so1"]
    assert so1["judge"] == "json_schema"
    assert so1["passed"] is False
    json.loads(so1["output"])  # output is still well-formed JSON
    # so2: object schema, correct -> matching object -> passes.
    so2 = by_id["so2"]
    assert so2["judge"] == "json_schema"
    assert so2["passed"] is True


def test_no_llm_cases_in_default_evalset():
    """The committed offline default evalset must contain ZERO llm-judge cases."""
    with open(EVALSET) as f:
        data = json.load(f)
    judges_used = {c.get("judge", "contains") for c in data["cases"]}
    assert "llm" not in judges_used, f"default evalset must not use llm judge: {judges_used}"


def test_history_appended_and_run_id_increments(tmp_path):
    out = tmp_path / "results.json"
    hist = tmp_path / "history.json"

    run(str(EVALSET), "mock", str(out), str(hist))
    run(str(EVALSET), "mock", str(out), str(hist))

    with open(hist) as f:
        history = json.load(f)
    assert isinstance(history, list)
    assert len(history) == 2
    assert history[0]["run_id"] == "run-0001"
    assert history[1]["run_id"] == "run-0002"
    for entry in history:
        for k in ("run_id", "timestamp", "pass_rate", "accuracy", "avg_latency_ms"):
            assert k in entry


def test_parallel_workers_same_results(tmp_path):
    """workers=4 must produce same ordered results as sequential run."""
    out_seq = tmp_path / "results_seq.json"
    out_par = tmp_path / "results_par.json"
    hist_seq = tmp_path / "hist_seq.json"
    hist_par = tmp_path / "hist_par.json"

    doc_seq = run(str(EVALSET), "mock", str(out_seq), str(hist_seq), workers=1)
    doc_par = run(str(EVALSET), "mock", str(out_par), str(hist_par), workers=4)

    # Same number of cases
    assert len(doc_par["cases"]) == len(doc_seq["cases"])

    # Same order (evalset order preserved)
    for seq_c, par_c in zip(doc_seq["cases"], doc_par["cases"]):
        assert seq_c["id"] == par_c["id"], "order mismatch"
        assert seq_c["passed"] == par_c["passed"]
        assert seq_c["score"] == par_c["score"]

    # Summary matches
    assert doc_par["summary"]["passed"] == doc_seq["summary"]["passed"]
    assert doc_par["summary"]["pass_rate"] == doc_seq["summary"]["pass_rate"]
