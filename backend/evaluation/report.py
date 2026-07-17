"""Aggregate per-item evaluation results into markdown / summary reports."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluation.metrics import mean, percent


EVAL_DIR = Path(__file__).resolve().parent
REPORTS_DIR = EVAL_DIR / "reports"
RESULTS_DIR = EVAL_DIR / "results"


def _default_output_paths() -> tuple[Path, Path]:
    """Timestamped paths so each run keeps its own report / results file."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (
        REPORTS_DIR / f"report_{stamp}.md",
        RESULTS_DIR / f"results_{stamp}.json",
    )


def _collect_intent_scores(results: list[dict[str, Any]]) -> dict[str, float | None]:
    f1s: list[float] = []
    precisions: list[float] = []
    recalls: list[float] = []

    for item in results:
        intent = (item.get("evaluations") or {}).get("intent") or {}
        if not intent.get("implemented"):
            continue
        score = intent.get("score") or {}
        if "f1" in score:
            f1s.append(float(score["f1"]))
        if "precision" in score:
            precisions.append(float(score["precision"]))
        if "recall" in score:
            recalls.append(float(score["recall"]))

    if not f1s:
        return {"accuracy": None, "precision": None, "recall": None, "f1": None}

    return {
        # 准确率：多标签场景下使用平均 F1
        "accuracy": mean(f1s),
        "precision": mean(precisions),
        "recall": mean(recalls),
        "f1": mean(f1s),
    }


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
    intent_scores = _collect_intent_scores(results)
    tool_scores = _collect_tool_scores(results)
    evidence_scores = _collect_evidence_scores(results)
    reasoning_scores = _collect_reasoning_scores(results)

    return {
        "total": len(results),
        "errors": len(errors),
        "intent_accuracy": intent_scores["accuracy"],
        "intent_precision": intent_scores["precision"],
        "intent_recall": intent_scores["recall"],
        "intent_f1": intent_scores["f1"],
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
            return "暂未实现"
        return percent(value)

    def fmt_score_100(value: float | None) -> str:
        if value is None:
            return "暂未实现"
        return f"{value:.0f}" if float(value).is_integer() else f"{value:.1f}"

    lines = [
        "# Agent 评测报告",
        "",
        "## 基础信息",
        "",
        f"测试问题数量：",
        f"{summary.get('total', 0)}",
        "",
        f"错误数量：",
        f"{summary.get('errors', 0)}",
        "",
        "",
        "## 综合指标",
        "",
        "",
        "### 意图理解",
        "",
        "",
        "准确率：",
        "",
        f"{fmt_ratio(summary.get('intent_accuracy'))}",
        "",
        "",
        "",
        "### 工具选择能力",
        "",
        "",
        "工具 Precision:",
        "",
        f"{fmt_ratio(summary.get('tool_precision'))}",
        "",
        "",
        "工具 Recall:",
        "",
        f"{fmt_ratio(summary.get('tool_recall'))}",
        "",
        "",
        "工具 F1:",
        "",
        f"{fmt_ratio(summary.get('tool_f1'))}",
        "",
        "",
        "",
        "### 证据质量",
        "",
        "",
        "平均分:",
        "",
        f"{fmt_score_100(summary.get('evidence_quality'))}",
        "",
        "",
        "证据完整性:",
        "",
        f"{fmt_score_100(summary.get('evidence_completeness'))}",
        "",
        "",
        "证据新鲜度:",
        "",
        f"{fmt_score_100(summary.get('evidence_freshness'))}",
        "",
        "",
        "证据覆盖:",
        "",
        f"{fmt_score_100(summary.get('evidence_coverage'))}",
        "",
        "",
        "",
        "### 推理质量",
        "",
        "",
        "平均分:",
        "",
        f"{fmt_score_100(summary.get('reasoning_quality'))}",
        "",
        "",
        "",
        "### 响应质量",
        "",
        "",
        "暂未实现",
        "",
        "",
        "",
        "### 平均延迟",
        "",
        "",
        f"{summary.get('average_latency_seconds', 0.0):.1f} 秒",
        "",
        "",
        "## 逐题结果",
        "",
        "| ID | 预期意图 | 预测意图 | 意图分 | 工具P | 工具R | 证据 | 推理 | 延迟(秒) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for item in results:
        tool = (item.get("evaluations") or {}).get("tool_selection") or {}
        tool_score = tool.get("score") or {}
        evidence = (item.get("evaluations") or {}).get("evidence") or {}
        reasoning = (item.get("evaluations") or {}).get("reasoning") or {}
        expected = ", ".join(item.get("expected_intents") or []) or "-"
        predicted = ", ".join(item.get("predicted_intents") or []) or "-"
        intent_score = item.get("intent_score")
        intent_display = "-" if intent_score is None else str(intent_score)

        if item.get("error"):
            lines.append(
                f"| {item.get('id')} | {expected} | {predicted} | {intent_display} | "
                f"错误 | 错误 | 错误 | 错误 | {item.get('latency_seconds', 0):.2f} |"
            )
            continue

        lines.append(
            "| {id} | {expected} | {predicted} | {intent} | {prec} | {rec} | "
            "{ev} | {rs} | {lat:.2f} |".format(
                id=item.get("id"),
                expected=expected,
                predicted=predicted,
                intent=intent_display,
                prec=percent(float(tool_score.get("precision", 0.0))),
                rec=percent(float(tool_score.get("recall", 0.0))),
                ev=evidence.get("score", "-"),
                rs=reasoning.get("score", "-"),
                lat=float(item.get("latency_seconds") or 0.0),
            )
        )

    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- Layer 1 意图理解、Layer 2 工具选择、Layer 3 证据质量、Layer 4 推理质量已实现。",
            "- 响应质量评测暂未实现。",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(
    results: list[dict[str, Any]],
    report_path: Path | None = None,
    results_path: Path | None = None,
) -> dict[str, Any]:
    if report_path is None or results_path is None:
        default_report, default_results = _default_output_paths()
        report_path = report_path or default_report
        results_path = results_path or default_results

    summary = summarize(results)
    markdown = render_markdown(summary, results)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(markdown, encoding="utf-8")
    results_path.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary["report_path"] = str(report_path)
    summary["results_path"] = str(results_path)
    return summary
