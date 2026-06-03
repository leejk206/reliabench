"""argparse CLI for reliabench."""

from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Optional

from .runner import run


def _print_summary(doc: Dict) -> None:
    meta = doc["meta"]
    s = doc["summary"]
    print()
    print(f"  reliabench  {meta['run_id']}  ({meta['model']} / {meta['evalset']})")
    print(f"  {meta['timestamp']}")
    print("  " + "-" * 48)
    print(f"  total           {s['total']}")
    print(f"  passed          {s['passed']}")
    print(f"  pass_rate       {s['pass_rate']:.3f}")
    print(f"  accuracy        {s['accuracy']:.3f}")
    print(f"  avg_latency_ms  {s['avg_latency_ms']}")
    print("  " + "-" * 48)
    print("  category        total  passed  pass_rate")
    for cat, c in s["categories"].items():
        print(f"  {cat:<14}  {c['total']:>5}  {c['passed']:>6}  {c['pass_rate']:>9.3f}")
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reliabench", description="LLM/agent reliability eval harness")
    sub = parser.add_subparsers(dest="command", required=True)

    runp = sub.add_parser("run", help="run an evalset against a model")
    runp.add_argument("--evalset", required=True, help="path to evalset JSON")
    runp.add_argument("--model", required=True, help="model id (mock | claude* | gpt*)")
    runp.add_argument("--out", required=True, help="path to write results.json")
    runp.add_argument("--history", required=True, help="path to history.json (created if absent)")
    runp.add_argument("--threshold", type=float, default=1.0, help="pass threshold (default 1.0)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        doc = run(
            evalset_path=args.evalset,
            model=args.model,
            out_path=args.out,
            history_path=args.history,
            threshold=args.threshold,
        )
        _print_summary(doc)
        print(f"  wrote {args.out}")
        print(f"  appended history -> {args.history}")
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
