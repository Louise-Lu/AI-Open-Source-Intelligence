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


def _collect_evidence_scores(results: list[dict[str, Any]]) -> dict[str, float]:
    overall: list[float] = []
    completeness: list[float] = []
    freshness: list[float] = []
    coverage: list[float] = []

    for item in results:
        evidence = (item.get("evaluations") or {}).get("evidence") or {}
        if not evidence.get("implemented"):
            continue
        if evidence.get("score") is not None:
            overall.append(float(evidence["score"]))
        details = evidence.get("details") or {}
        if details.get("completeness") is not None:
            completeness.append(float(details["completeness"]))
        if details.get("freshness") is not None:
            freshness.append(float(details["freshness"]))
        if details.get("coverage") is not None:
            coverage.append(float(details["coverage"]))

    return {
        "quality": mean(overall),
        "completeness": mean(completeness),
        "freshness": mean(freshness),
        "coverage": mean(coverage),
    }


def _collect_reasoning_scores(results: list[dict[str, Any]]) -> dict[str, float]:
    overall: list[float] = []
    grounding: list[float] = []
    contradictions: list[float] = []
    completeness: list[float] = []

    for item in results:
        reasoning = (item.get("evaluations") or {}).get("reasoning") or {}
        if not reasoning.get("implemented"):
            continue
        if reasoning.get("score") is not None:
            overall.append(float(reasoning["score"]))
        details = reasoning.get("details") or {}
        if details.get("grounding") is not None:
            grounding.append(float(details["grounding"]))
        if details.get("contradictions") is not None:
            contradictions.append(float(details["contradictions"]))
        if details.get("completeness") is not None:
            completeness.append(float(details["completeness"]))

    return {
        "quality": mean(overall),
        "grounding": mean(grounding),
        "contradictions": mean(contradictions),
        "completeness": mean(completeness),
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [
        float(item["latency_seconds"])
        for item in results
        if item.get("latency_seconds") is not None and not item.get("error")
    ]
    errors = [item for item in results if item.get("error")]
    tool_scores = _collect_tool_scores(results)
    evidence_scores = _collect_evidence_scores(results)
    reasoning_scores = _collect_reasoning_scores(results)

    return {
        "total": len(results),
        "errors": len(errors),
        "intent_accuracy": None,
        "tool_precision": tool_scores["precision"],
        "tool_recall": tool_scores["recall"],
        "tool_f1": tool_scores["f1"],
        "tool_order": tool_scores["order"],
        "evidence_quality": evidence_scores["quality"],
        "evidence_completeness": evidence_scores["completeness"],
        "evidence_freshness": evidence_scores["freshness"],
        "evidence_coverage": evidence_scores["coverage"],
        "reasoning_quality": reasoning_scores["quality"],
        "reasoning_grounding": reasoning_scores["grounding"],
        "reasoning_contradictions": reasoning_scores["contradictions"],
        "reasoning_completeness": reasoning_scores["completeness"],
        "answer_quality": None,
        "average_latency_seconds": mean(latencies),
    }


def render_markdown(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    def fmt_ratio(value: float | None) -> str:
        if value is None:
            return "N/A (stub)"
        return percent(value)

    def fmt_score_100(value: float | None) -> str:
        if value is None:
            return "N/A (stub)"
        return f"{value:.1f}"

    lines = [
        "# Agent Evaluation Report",
        "",
        f"Total questions: {summary.get('total', 0)}",
        f"Errors: {summary.get('errors', 0)}",
        "",
        "## Aggregate Metrics",
        "",
        "Intent Accuracy",
        "",
        f"{fmt_ratio(summary.get('intent_accuracy'))}",
        "",
        "Tool Precision",
        "",
        f"{fmt_ratio(summary.get('tool_precision'))}",
        "",
        "Tool Recall",
        "",
        f"{fmt_ratio(summary.get('tool_recall'))}",
        "",
        "Tool F1",
        "",
        f"{fmt_ratio(summary.get('tool_f1'))}",
        "",
        "Tool Call Order",
        "",
        f"{fmt_ratio(summary.get('tool_order'))}",
        "",
        "## Evidence Quality",
        "",
        "Average Score:",
        "",
        f"{fmt_score_100(summary.get('evidence_quality'))}",
        "",
        "Evidence Completeness",
        "",
        f"{fmt_score_100(summary.get('evidence_completeness'))}",
        "",
        "Evidence Freshness",
        "",
        f"{fmt_score_100(summary.get('evidence_freshness'))}",
        "",
        "Evidence Coverage",
        "",
        f"{fmt_score_100(summary.get('evidence_coverage'))}",
        "",
        "## Reasoning Quality",
        "",
        "Average Score:",
        "",
        f"{fmt_score_100(summary.get('reasoning_quality'))}",
        "",
        "Evidence Grounding",
        "",
        f"{fmt_score_100(summary.get('reasoning_grounding'))}",
        "",
        "Contradiction Detection",
        "",
        f"{fmt_score_100(summary.get('reasoning_contradictions'))}",
        "",
        "Reasoning Completeness",
        "",
        f"{fmt_score_100(summary.get('reasoning_completeness'))}",
        "",
        "Answer Quality",
        "",
        "N/A (stub)",
        "",
        "Average Latency",
        "",
        f"{summary.get('average_latency_seconds', 0.0):.2f} seconds",
        "",
        "## Per-Question Results",
        "",
        "| ID | Intent | Tool P | Tool R | Evidence | Reasoning | Unsupported | Latency (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for item in results:
        tool = (item.get("evaluations") or {}).get("tool_selection") or {}
        tool_score = tool.get("score") or {}
        evidence = (item.get("evaluations") or {}).get("evidence") or {}
        reasoning = (item.get("evaluations") or {}).get("reasoning") or {}
        reasoning_details = reasoning.get("details") or {}
        if item.get("error"):
            lines.append(
                f"| {item.get('id')} | {item.get('intent', '')} | ERR | ERR | "
                f"ERR | ERR | - | {item.get('latency_seconds', 0):.2f} |"
            )
            continue

        unsupported = ", ".join(reasoning_details.get("unsupported_claims") or []) or "-"
        lines.append(
            "| {id} | {intent} | {prec} | {rec} | {ev} | {rs} | {unsupported} | {lat:.2f} |".format(
                id=item.get("id"),
                intent=item.get("intent", ""),
                prec=percent(float(tool_score.get("precision", 0.0))),
                rec=percent(float(tool_score.get("recall", 0.0))),
                ev=evidence.get("score", "N/A"),
                rs=reasoning.get("score", "N/A"),
                unsupported=unsupported,
                lat=float(item.get("latency_seconds") or 0.0),
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Layer 2 Tool Selection, Layer 3 Evidence Quality, and Layer 4 Reasoning Quality are implemented.",
            "- Intent / Answer evaluators remain stubs.",
            "",
        ]
    )
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
