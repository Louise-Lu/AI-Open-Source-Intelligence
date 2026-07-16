"""
Evaluation runner — Phase 1.

Reads dataset → calls Agent via ChatService → evaluates → writes report.

Usage (from backend/):

    python -m evaluation.runner
    python -m evaluation.runner --limit 5
    python -m evaluation.runner --ids 1,2,3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# Ensure `backend/` is on sys.path when run as a script.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.evaluators import (  # noqa: E402
    evaluate_answer,
    evaluate_evidence,
    evaluate_intent,
    evaluate_reasoning,
    evaluate_tool_selection,
)
from evaluation.report import write_report  # noqa: E402
from services.chat_service import ChatService  # noqa: E402


EVAL_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVAL_DIR / "dataset" / "questions.json"


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON list of question objects.")
    return data


def build_prompt(item: dict[str, Any]) -> str:
    """
    Keep the user question as-is. Dataset `repo` is metadata for evaluators;
    questions already name the repository when needed.
    """
    return item["question"]


def run_one(service: ChatService, item: dict[str, Any]) -> dict[str, Any]:
    question = build_prompt(item)
    started = time.perf_counter()
    error = None
    answer = ""
    trace: list[dict[str, Any]] = []

    try:
        result = service.chat(question)
        answer = result.get("answer") or ""
        trace = result.get("trace") or []
    except Exception as exc:  # noqa: BLE001 — keep run going across dataset
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()

    latency = time.perf_counter() - started

    record: dict[str, Any] = {
        "id": item.get("id"),
        "question": question,
        "repo": item.get("repo"),
        "intent": item.get("intent"),
        "expected_tools": item.get("expected_tools"),
        "answer": answer,
        "trace": trace,
        "latency_seconds": round(latency, 3),
        "error": error,
        "evaluations": {},
    }

    # Always run evaluators (tool selection still scores empty trace on failure).
    record["evaluations"] = {
        "intent": evaluate_intent(item, answer, trace),
        "tool_selection": evaluate_tool_selection(item, answer, trace),
        "evidence": evaluate_evidence(item, answer, trace),
        "reasoning": evaluate_reasoning(item, answer, trace),
        "answer": evaluate_answer(item, answer, trace),
    }
    return record


def run(
    limit: int | None = None,
    ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    dataset = load_dataset()

    if ids:
        id_set = set(ids)
        dataset = [item for item in dataset if item.get("id") in id_set]

    if limit is not None:
        dataset = dataset[:limit]

    service = ChatService()
    results: list[dict[str, Any]] = []

    print(f"Running evaluation on {len(dataset)} question(s)...")
    for index, item in enumerate(dataset, start=1):
        print(f"[{index}/{len(dataset)}] id={item.get('id')} intent={item.get('intent')}")
        record = run_one(service, item)
        results.append(record)

        tool = record["evaluations"]["tool_selection"]["score"]
        status = "ERROR" if record["error"] else "OK"
        print(
            f"  → {status}  P={tool['precision']:.2f}  R={tool['recall']:.2f}  "
            f"order={tool['order']:.2f}  latency={record['latency_seconds']:.2f}s"
        )

    summary = write_report(results)
    print("\n=== Summary ===")
    print(f"Tool Precision: {summary['tool_precision'] * 100:.1f}%")
    print(f"Tool Recall:    {summary['tool_recall'] * 100:.1f}%")
    print(f"Tool Order:     {summary['tool_order'] * 100:.1f}%")
    print(f"Avg Latency:    {summary['average_latency_seconds']:.2f}s")
    print(f"Report written: {EVAL_DIR / 'report.md'}")
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Agent Evaluation Runner (Phase 1)")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only run the first N questions.",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help="Comma-separated question ids, e.g. 1,2,5",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    ids = None
    if args.ids:
        ids = [int(part.strip()) for part in args.ids.split(",") if part.strip()]
    run(limit=args.limit, ids=ids)


if __name__ == "__main__":
    main()
