"""
Evaluation runner.

Reads dataset → Intent Router → Agent → evaluates → writes report.

Usage (from backend/):

    python -m evaluation.run
    python -m evaluation.runner
    python -m evaluation.run --limit 5
    python -m evaluation.run --ids 1,2,3
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
from evaluation.evidence_from_trace import evidence_from_trace  # noqa: E402
from evaluation.intent_router import IntentRouter  # noqa: E402
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


def _expected_intents(item: dict[str, Any]) -> list[str]:
    if "expected_intents" in item:
        return list(item.get("expected_intents") or [])
    legacy = item.get("intent")
    if isinstance(legacy, str) and legacy:
        return [legacy]
    if isinstance(legacy, list):
        return list(legacy)
    return []


def run_one(
    service: ChatService,
    intent_router: IntentRouter,
    item: dict[str, Any],
) -> dict[str, Any]:
    question = build_prompt(item)
    expected_intents = _expected_intents(item)

    # 1. Intent Router (Layer 1)
    predicted_intents: list[str] = []
    intent_error = None
    try:
        predicted_intents = intent_router.classify(question)
    except Exception as exc:  # noqa: BLE001
        intent_error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()

    started = time.perf_counter()
    error = intent_error
    answer = ""
    trace: list[dict[str, Any]] = []

    try:
        result = service.chat(question)
        answer = result.get("answer") or ""
        trace = result.get("trace") or []
    except Exception as exc:  # noqa: BLE001 — keep run going across dataset
        agent_error = f"{type(exc).__name__}: {exc}"
        error = f"{error}; {agent_error}" if error else agent_error
        traceback.print_exc()

    latency = time.perf_counter() - started
    evidence = evidence_from_trace(trace)

    # 2–5. Tool / Evidence / Reasoning / Answer
    intent_eval = evaluate_intent(item, predicted_intents)
    intent_score = (intent_eval.get("score") or {}).get("intent_score")

    record: dict[str, Any] = {
        "id": item.get("id"),
        "question": question,
        "repo": item.get("repo"),
        "expected_intents": expected_intents,
        "predicted_intents": predicted_intents,
        "intent_score": intent_score,
        "expected_tools": item.get("expected_tools"),
        "required_evidence": item.get("required_evidence"),
        "answer": answer,
        "trace": trace,
        "evidence": evidence,
        "latency_seconds": round(latency, 3),
        "error": error,
        "evaluations": {
            "intent": intent_eval,
            "tool_selection": evaluate_tool_selection(item, answer, trace),
            "evidence": evaluate_evidence(item, evidence, answer),
            "reasoning": evaluate_reasoning(item, evidence, answer),
            "answer": evaluate_answer(item, answer, trace),
        },
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
    intent_router = IntentRouter()
    results: list[dict[str, Any]] = []

    print(f"正在评测 {len(dataset)} 个问题...")
    for index, item in enumerate(dataset, start=1):
        expected = _expected_intents(item)
        print(f"[{index}/{len(dataset)}] id={item.get('id')} intents={expected}")
        record = run_one(service, intent_router, item)
        results.append(record)

        intent_score = record.get("intent_score")
        tool = record["evaluations"]["tool_selection"]["score"]
        evidence_score = record["evaluations"]["evidence"]["score"]
        reasoning_score = record["evaluations"]["reasoning"]["score"]
        answer_score = record["evaluations"]["answer"]["score"]
        status = "错误" if record["error"] else "成功"
        print(
            f"  → {status}  意图={intent_score}  "
            f"工具P={tool['precision']:.2f}  工具R={tool['recall']:.2f}  "
            f"证据={evidence_score}  推理={reasoning_score}  "
            f"响应={answer_score}  "
            f"延迟={record['latency_seconds']:.2f}s"
        )

    summary = write_report(results)
    print("\n=== 评测摘要 ===")
    intent_acc = summary.get("intent_accuracy")
    intent_display = f"{intent_acc * 100:.1f}%" if intent_acc is not None else "暂未实现"
    print(f"意图准确率:     {intent_display}")
    print(f"工具 Precision: {summary['tool_precision'] * 100:.1f}%")
    print(f"工具 Recall:    {summary['tool_recall'] * 100:.1f}%")
    print(f"证据质量:       {summary['evidence_quality']:.1f}")
    print(f"推理质量:       {summary['reasoning_quality']:.1f}")
    answer_quality = summary.get("answer_quality")
    answer_display = (
        f"{answer_quality:.1f}" if answer_quality is not None else "暂未实现"
    )
    print(f"响应质量:       {answer_display}")
    print(f"平均延迟:       {summary['average_latency_seconds']:.2f}s")
    print(f"报告已写入:     {summary.get('report_path')}")
    print(f"结果已写入:     {summary.get('results_path')}")
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Agent 评测 Runner")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="只运行前 N 个问题。",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help="逗号分隔的问题 id，例如 1,2,5",
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
