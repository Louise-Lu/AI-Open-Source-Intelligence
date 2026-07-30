"""AI Intelligence Agent Evaluation Report.

报告结构:
  1. Intent Understanding — 意图理解准确率
  2. Context Planning — 计划质量
  3. Agent Exploration — 工具效率 + 来源覆盖
  4. Evidence — 证据质量
  5. Research — 研究完整性
  6. Performance — 延迟 + 成本
"""

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
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (
        REPORTS_DIR / f"report_{stamp}.md",
        RESULTS_DIR / f"results_{stamp}.json",
    )


# ── 指标收集 ──────────────────────────────────────────────


def _safe_score(eval_result: dict[str, Any] | None) -> float | None:
    """安全提取 evaluator 的 score。"""
    if not eval_result:
        return None
    if not eval_result.get("implemented"):
        return None
    return eval_result.get("score")


def _collect_scores(
    results: list[dict[str, Any]],
    eval_key: str,
) -> list[float]:
    """从 results 中收集某个 evaluator 的分数。"""
    scores: list[float] = []
    for item in results:
        if item.get("error"):
            continue
        ev = (item.get("evaluations") or {}).get(eval_key) or {}
        s = _safe_score(ev)
        if s is not None:
            scores.append(float(s))
    return scores


def _collect_detail_values(
    results: list[dict[str, Any]],
    eval_key: str,
    detail_key: str,
) -> list[float]:
    """从 evaluator details 中收集特定值。"""
    values: list[float] = []
    for item in results:
        if item.get("error"):
            continue
        ev = (item.get("evaluations") or {}).get(eval_key) or {}
        details = ev.get("details") or {}
        val = details.get(detail_key)
        if val is not None:
            values.append(float(val))
    return values


# ── 综合分权重配置 ──
OVERALL_WEIGHTS = {
    "intent_accuracy": 0.12,
    "context_builder": 0.08,
    "tool_efficiency": 0.12,
    "evidence_quality": 0.20,
    "research_completeness": 0.28,
    "answer_quality": 0.12,
    "runtime_performance": 0.08,
}


def _normalize_score(score: float | None, eval_key: str) -> float | None:
    """将各评估器的分数归一化到 0-100 尺度。

    Research Completeness 原始范围 1-5，需转换为 0-100。
    Answer Quality 已经是 0-100。
    """
    if score is None:
        return None
    if eval_key == "research_completeness":
        # 1-5 → 0-100
        return max(0.0, min(100.0, (score - 1.0) / 4.0 * 100.0))
    return float(score)


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总所有评测结果。"""
    latencies = [
        float(item["latency_seconds"])
        for item in results
        if item.get("latency_seconds") is not None and not item.get("error")
    ]
    errors = [item for item in results if item.get("error")]

    # 1. Intent Accuracy
    intent_scores = _collect_scores(results, "intent_accuracy")
    intent_acc = mean(intent_scores) if intent_scores else None

    # 2. ContextBuilder
    context_scores = _collect_scores(results, "context_builder")
    context_plan = mean(context_scores) if context_scores else None

    # 3. Tool Efficiency
    tool_eff_scores = _collect_scores(results, "tool_efficiency")
    tool_efficiency = mean(tool_eff_scores) if tool_eff_scores else None
    source_recalls = _collect_detail_values(results, "tool_efficiency", "source_recall")
    source_recall = mean(source_recalls) if source_recalls else None
    tool_precisions = _collect_detail_values(results, "tool_efficiency", "tool_precision")
    tool_precision = mean(tool_precisions) if tool_precisions else None
    tool_f1s = _collect_detail_values(results, "tool_efficiency", "f1")
    tool_f1 = mean(tool_f1s) if tool_f1s else None
    param_accs = _collect_detail_values(results, "tool_efficiency", "parameter_accuracy")
    param_accuracy = mean(param_accs) if param_accs else None
    total_tool_calls = _collect_detail_values(results, "tool_efficiency", "total_tool_calls")
    avg_tool_calls = mean(total_tool_calls) if total_tool_calls else None

    # 4. Evidence Quality
    evidence_scores = _collect_scores(results, "evidence_quality")
    evidence_quality = mean(evidence_scores) if evidence_scores else None

    # 5. Research Completeness (原始 1-5)
    completeness_scores = _collect_scores(results, "research_completeness")
    completeness = mean(completeness_scores) if completeness_scores else None

    # 5b. Answer Quality (0-100, 如果存在)
    answer_scores = _collect_scores(results, "answer_quality")
    answer_quality = mean(answer_scores) if answer_scores else None

    # 6. Runtime Performance
    perf_scores = _collect_scores(results, "runtime_performance")
    perf_score = mean(perf_scores) if perf_scores else None
    total_costs = _collect_detail_values(results, "runtime_performance", "estimated_cost_yuan")
    total_cost = sum(total_costs) if total_costs else 0.0

    # ── 加权综合分 (Overall Quality Score, 0-100) ──
    normalized = {
        "intent_accuracy": _normalize_score(intent_acc, "intent_accuracy"),
        "context_builder": _normalize_score(context_plan, "context_builder"),
        "tool_efficiency": _normalize_score(tool_efficiency, "tool_efficiency"),
        "evidence_quality": _normalize_score(evidence_quality, "evidence_quality"),
        "research_completeness": _normalize_score(completeness, "research_completeness"),
        "answer_quality": _normalize_score(answer_quality, "answer_quality"),
        "runtime_performance": _normalize_score(perf_score, "runtime_performance"),
    }
    # 动态调整权重：如果某个维度没有数据，重新分配权重
    active_weights = {k: v for k, v in OVERALL_WEIGHTS.items() if normalized.get(k) is not None}
    total_weight = sum(active_weights.values())
    if total_weight > 0:
        overall_score = sum(
            (normalized[k] or 0) * (w / total_weight)
            for k, w in active_weights.items()
        )
    else:
        overall_score = None

    # 按类别汇总
    categories: dict[str, dict[str, Any]] = {}
    for item in results:
        cat = item.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"count": 0, "errors": 0, "intent": [], "completeness": []}
        categories[cat]["count"] += 1
        if item.get("error"):
            categories[cat]["errors"] += 1
        ev = item.get("evaluations") or {}
        intent_ev = ev.get("intent_accuracy") or {}
        if _safe_score(intent_ev) is not None:
            categories[cat]["intent"].append(float(_safe_score(intent_ev)))
        comp_ev = ev.get("research_completeness") or {}
        if _safe_score(comp_ev) is not None:
            categories[cat]["completeness"].append(float(_safe_score(comp_ev)))

    return {
        "total": len(results),
        "errors": len(errors),
        # Intent
        "intent_accuracy": intent_acc,
        # Context
        "context_plan_score": context_plan,
        # Tool
        "tool_efficiency": tool_efficiency,
        "source_recall": source_recall,
        "tool_precision": tool_precision,
        "tool_f1": tool_f1,
        "parameter_accuracy": param_accuracy,
        "avg_tool_calls": avg_tool_calls,
        # Evidence
        "evidence_quality": evidence_quality,
        # Completeness (原始 1-5)
        "completeness_score": completeness,
        # Answer Quality (0-100)
        "answer_quality": answer_quality,
        # Performance
        "avg_latency_seconds": mean(latencies),
        "total_estimated_cost": total_cost,
        # Overall (0-100)
        "overall_score": round(overall_score, 1) if overall_score is not None else None,
        # Categories
        "categories": categories,
        # Display strings
        "overall_display": f"{overall_score:.1f}" if overall_score is not None else "-",
        "intent_accuracy_display": f"{intent_acc:.1f}%" if intent_acc is not None else "-",
        "context_plan_display": f"{context_plan:.1f}%" if context_plan is not None else "-",
        "avg_tool_calls_display": f"{avg_tool_calls:.1f}" if avg_tool_calls is not None else "-",
        "tool_efficiency_display": f"{tool_efficiency:.1f}%" if tool_efficiency is not None else "-",
        "source_recall_display": f"{source_recall * 100:.1f}%" if source_recall is not None else "-",
        "evidence_quality_display": f"{evidence_quality:.0f}" if evidence_quality is not None else "-",
        "completeness_display": f"{completeness:.1f}/5" if completeness is not None else "-",
        "answer_quality_display": f"{answer_quality:.0f}" if answer_quality is not None else "-",
        "avg_latency_display": f"{mean(latencies):.1f}s" if latencies else "-",
        "total_cost_display": f"¥{total_cost:.4f}" if total_cost else "-",
    }


def render_markdown(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    """生成 Markdown 报告。"""

    def fmt_pct(value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value:.1f}%"

    def fmt_score(value: float | None, max_val: int = 100) -> str:
        if value is None:
            return "-"
        return f"{value:.1f}" if max_val > 5 else f"{value:.1f}/5"

    lines = [
        "# AI Intelligence Agent Evaluation Report",
        "",
        "## 基础信息",
        "",
        f"测试用例数量：{summary.get('total', 0)}",
        "",
        f"错误数量：{summary.get('errors', 0)}",
        "",
        f"**综合分 (Overall): {summary.get('overall_display', '-')}**",
        "",
        "---",
        "",
        "## Intent Understanding",
        "",
        f"**Accuracy: {summary.get('intent_accuracy_display', '-')}**",
        "",
        "---",
        "",
        "## Context Planning",
        "",
        f"**Score: {summary.get('context_plan_display', '-')}**",
        "",
        "---",
        "",
        "## Agent Exploration",
        "",
        f"- Average Tool Calls: {summary.get('avg_tool_calls_display', '-')}",
        f"- Tool Efficiency: {summary.get('tool_efficiency_display', '-')}",
        f"- Source Recall: {summary.get('source_recall_display', '-')}",
        f"- Tool Precision: {fmt_pct(summary.get('tool_precision') * 100 if summary.get('tool_precision') is not None else None)}",
        f"- Tool F1: {fmt_pct(summary.get('tool_f1') * 100 if summary.get('tool_f1') is not None else None)}",
        f"- Parameter Accuracy: {fmt_pct(summary.get('parameter_accuracy') * 100 if summary.get('parameter_accuracy') is not None else None)}",
        "",
        "---",
        "",
        "## Evidence",
        "",
        f"**Quality: {summary.get('evidence_quality_display', '-')}**",
        "",
        "---",
        "",
        "## Research",
        "",
        f"**Completeness Score: {summary.get('completeness_display', '-')}**",
        "",
        "---",
        "",
        "## Answer Quality",
        "",
        f"**Score: {summary.get('answer_quality_display', '-')}**",
        "",
        "---",
        "",
        "## Performance",
        "",
        f"- Latency: {summary.get('avg_latency_display', '-')}",
        f"- Cost: {summary.get('total_cost_display', '-')}",
        "",
        "---",
        "",
        "## 逐题结果",
        "",
    ]

    for item in results:
        case_id = item.get("id")
        query = item.get("query") or ""
        category = item.get("category", "unknown")
        ev = item.get("evaluations") or {}

        intent_ev = ev.get("intent_accuracy") or {}
        context_ev = ev.get("context_builder") or {}
        tool_ev = ev.get("tool_efficiency") or {}
        evidence_ev = ev.get("evidence_quality") or {}
        completeness_ev = ev.get("research_completeness") or {}
        answer_ev = ev.get("answer_quality") or {}
        perf_ev = ev.get("runtime_performance") or {}

        intent_score = _safe_score(intent_ev)
        context_score = _safe_score(context_ev)
        tool_score = _safe_score(tool_ev)
        evidence_score = _safe_score(evidence_ev)
        completeness_score = _safe_score(completeness_ev)
        answer_score = _safe_score(answer_ev)
        latency = item.get("latency_seconds", 0)

        tool_details = tool_ev.get("details") or {}
        completeness_details = completeness_ev.get("details") or {}

        lines.append(f"### Q{case_id} [{category}]: {query}")
        lines.append("")

        # 汇总表
        lines.append("| 意图 | 计划 | 效率 | 证据 | 完整性 | 回答 | 延迟 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")

        if item.get("error"):
            lines.append(f"| 错误 | 错误 | 错误 | 错误 | 错误 | 错误 | {latency:.1f}s |")
        else:
            lines.append(
                f"| {fmt_pct(intent_score)} "
                f"| {fmt_pct(context_score)} "
                f"| {fmt_pct(tool_score)} "
                f"| {fmt_score(evidence_score)} "
                f"| {fmt_score(completeness_score, 5)} "
                f"| {fmt_score(answer_score)} "
                f"| {latency:.1f}s |"
            )

        lines.append("")

        # 详细信息
        if not item.get("error"):
            # Intent details
            intent_details = intent_ev.get("details") or {}
            lines.append(
                f"- 意图: objective={'✓' if intent_details.get('objective_match') else '✗'} "
                f"focus={intent_details.get('focus_score', '-')} "
                f"depth={'✓' if intent_details.get('depth_match') else '✗'}"
            )

            # Tool details
            param_acc = tool_details.get("parameter_accuracy")
            param_str = f" 参数={param_acc:.0%}" if param_acc is not None else ""
            lines.append(
                f"- 工具: 总调用={tool_details.get('total_tool_calls', 0)} "
                f"有效={tool_details.get('useful_calls', 0)} "
                f"阻止={tool_details.get('blocked_calls', 0)} "
                f"来源={tool_details.get('called_sources', [])}"
                f"{param_str}"
            )

            # Missing sources
            missing = tool_details.get("missing_sources") or []
            if missing:
                lines.append(f"- 缺失来源: {', '.join(missing)}")

            # Evidence details
            ev_details = evidence_ev.get("details") or {}
            lines.append(
                f"- 证据: 等级={ev_details.get('base_level', 0)} "
                f"支撑率={ev_details.get('grounding_ratio', 0):.0%} "
                f"来源数={ev_details.get('unique_sources', 0)}"
            )

            # Completeness feedback
            feedback = completeness_details.get("feedback", "")
            if feedback:
                lines.append(f"- 评审: {feedback[:200]}")

            # Answer quality feedback
            answer_details = answer_ev.get("details") or {}
            answer_feedback = answer_details.get("feedback", "")
            if answer_feedback:
                lines.append(f"- 回答: {answer_feedback[:200]}")

        lines.append("")

    lines.extend([
        "---",
        "",
        "*AI Intelligence Agent Evaluation v2*",
        "",
    ])
    return "\n".join(lines)


def write_report(
    results: list[dict[str, Any]],
    report_path: Path | None = None,
    results_path: Path | None = None,
) -> dict[str, Any]:
    """生成并写入报告。"""
    if report_path is None or results_path is None:
        default_report, default_results = _default_output_paths()
        report_path = report_path or default_report
        results_path = results_path or default_results

    summary = summarize(results)
    markdown = render_markdown(summary, results)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(markdown, encoding="utf-8")

    # 写入 JSON 结果（截断过大的 full_trace 以控制文件大小）
    results_for_json = []
    for item in results:
        item_copy = dict(item)
        # 截断 tool_trace 中的 output（可能很大）
        full_trace = item_copy.get("full_trace") or {}
        tool_trace = full_trace.get("tool_trace") or []
        truncated_trace = []
        for step in tool_trace:
            step_copy = dict(step)
            output = step_copy.get("output") or step_copy.get("raw_output") or step_copy.get("observation")
            if isinstance(output, str) and len(output) > 500:
                if "raw_output" in step_copy:
                    step_copy["raw_output"] = output[:500] + "...[truncated]"
                if "observation" in step_copy:
                    step_copy["observation"] = output[:500] + "...[truncated]"
            truncated_trace.append(step_copy)
        full_trace_copy = dict(full_trace)
        full_trace_copy["tool_trace"] = truncated_trace
        item_copy["full_trace"] = full_trace_copy
        results_for_json.append(item_copy)

    results_path.write_text(
        json.dumps(
            {"summary": summary, "results": results_for_json},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    summary["report_path"] = str(report_path)
    summary["results_path"] = str(results_path)
    return summary
