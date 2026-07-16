"""Aggregate per-item evaluation results into markdown / summary reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.metrics import mean, percent


EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_REPORT_PATH = EVAL_DIR / "report.md"
DEFAULT_RESULTS_PATH = EVAL_DIR / "results" / "latest.json"


def _collect_tool_scores(results: list[dict[str, Any]]) -> dict[str, float]:
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []
    orders: list[float] = []

    for item in results:
        tool = (item.get("evaluations") or {}).get("tool_selection") or {}
        score = tool.get("score") or {}
        if not tool.get("implemented"):
            continue
        if "precision" in score:
            precisions.append(float(score["precision"]))
        if "recall" in score:
            recalls.append(float(score["recall"]))
        if "f1" in score:
            f1s.append(float(score["f1"]))
        if "order" in score:
            orders.append(float(score["order"]))

    return {
        "precision": mean(precisions),
        "recall": mean(recalls),
        "f1": mean(f1s),
        "order": mean(orders),
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [
        float(item["latency_seconds"])
        for item in results
        if item.get("latency_seconds") is not None and not item.get("error")
    ]
    errors = [item for item in results if item.get("error")]
    tool_scores = _collect_tool_scores(results)

    return {
        "total": len(results),
        "errors": len(errors),
        "intent_accuracy": None,
        "tool_precision": tool_scores["precision"],
        "tool_recall": tool_scores["recall"],
        "tool_f1": tool_scores["f1"],
        "tool_order": tool_scores["order"],
        "evidence_completeness": None,
        "reasoning": None,
        "answer_quality": None,
        "average_latency_seconds": mean(latencies),
    }


def render_markdown(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    def fmt_ratio(value: float | None) -> str:
        if value is None:
            return "N/A (Phase 1 stub)"
        return percent(value)

    def fmt_score_5(value: float | None) -> str:
        if value is None:
            return "N/A (Phase 1 stub)"
        return f"{value:.1f} / 5"

    lines = [
        "# Agent Evaluation Report",
        "",
        f"Total questions: {summary.get('total', 0)}",
        f"Errors: {summary.get('errors', 0)}",
        "",
        "## Aggregate Metrics",
        "",
        f"Intent Accuracy",
        "",
        f"{fmt_ratio(summary.get('intent_accuracy'))}",
        "",
        f"Tool Precision",
        "",
        f"{fmt_ratio(summary.get('tool_precision'))}",
        "",
        f"Tool Recall",
        "",
        f"{fmt_ratio(summary.get('tool_recall'))}",
        "",
        f"Tool F1",
        "",
        f"{fmt_ratio(summary.get('tool_f1'))}",
        "",
        f"Tool Call Order",
        "",
        f"{fmt_ratio(summary.get('tool_order'))}",
        "",
        f"Evidence Completeness",
        "",
        f"{fmt_ratio(summary.get('evidence_completeness'))}",
        "",
        f"Reasoning",
        "",
        f"{fmt_score_5(summary.get('reasoning'))}",
        "",
        f"Answer Quality",
        "",
        f"{fmt_score_5(summary.get('answer_quality'))}",
        "",
        f"Average Latency",
        "",
        f"{summary.get('average_latency_seconds', 0.0):.2f} seconds",
        "",
        "## Per-Question Tool Selection",
        "",
        "| ID | Intent | Precision | Recall | Missed | Extra | Latency (s) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for item in results:
        tool = (item.get("evaluations") or {}).get("tool_selection") or {}
        score = tool.get("score") or {}
        details = tool.get("details") or {}
        if item.get("error"):
            lines.append(
                f"| {item.get('id')} | {item.get('intent', '')} | ERR | ERR | "
                f"- | - | {item.get('latency_seconds', 0):.2f} |"
            )
            continue

        lines.append(
            "| {id} | {intent} | {prec} | {rec} | {missed} | {extra} | {lat:.2f} |".format(
                id=item.get("id"),
                intent=item.get("intent", ""),
                prec=percent(float(score.get("precision", 0.0))),
                rec=percent(float(score.get("recall", 0.0))),
                missed=", ".join(details.get("missed_tools") or []) or "-",
                extra=", ".join(details.get("extra_tools") or []) or "-",
                lat=float(item.get("latency_seconds") or 0.0),
            )
        )

    lines.extend(["", "## Notes", "", "- Phase 1 implements Tool Selection only.", ""])
    return "\n".join(lines)


def write_report(
    results: list[dict[str, Any]],
    report_path: Path | None = None,
    results_path: Path | None = None,
) -> dict[str, Any]:
    report_path = report_path or DEFAULT_REPORT_PATH
    results_path = results_path or DEFAULT_RESULTS_PATH

    summary = summarize(results)
    markdown = render_markdown(summary, results)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(markdown, encoding="utf-8")
    results_path.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return summary
