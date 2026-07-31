"""ExecutionPlan Evaluator 
评估 执行计划质量

检查 ExecutionPlan 是否合理：
- source_scope 是否覆盖预期来源
- required_evidence 是否正确
- tool budget 是否合理

输出: execution_plan_score (0-100)
source_scope(40%) + required_evidence(35%) + budget(25%)
"""

from __future__ import annotations

from typing import Any


def evaluate_execution_plan(
    case: dict[str, Any],
    execution_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    """评估 ExecutionPlan 质量。

    Args:
        case: 评测用例（含 expected_context）
        execution_plan: Agent 实际使用的 ExecutionPlan dict

    Returns:
        评估结果 dict
    """
    expected_plan = case.get("expected_plan") or {}
    if execution_plan is None:
        execution_plan = {}

    # 1. source_scope_match (40%) — F1 分数 (平衡 Precision 和 Recall)
    exp_preferred = set(expected_plan.get("source_scope") or [])
    plan_scope = set(execution_plan.get("source_scope") or [])
    if exp_preferred or plan_scope:
        scope_overlap = len(exp_preferred & plan_scope)
        scope_precision = scope_overlap / len(plan_scope) if plan_scope else 1.0
        scope_recall = scope_overlap / len(exp_preferred) if exp_preferred else 1.0
        scope_score = (
            2 * scope_precision * scope_recall / (scope_precision + scope_recall)
            if (scope_precision + scope_recall) > 0
            else 0.0
        )
    else:
        scope_score = 1.0

    # 2. required_evidence_match (35%) — F1 分数
    exp_required = set(expected_plan.get("required_evidence") or [])
    plan_required = set(execution_plan.get("required_evidence") or [])
    if exp_required or plan_required:
        req_overlap = len(exp_required & plan_required)
        req_precision = req_overlap / len(plan_required) if plan_required else 1.0
        req_recall = req_overlap / len(exp_required) if exp_required else 1.0
        required_score = (
            2 * req_precision * req_recall / (req_precision + req_recall)
            if (req_precision + req_recall) > 0
            else 0.0
        )
    else:
        required_score = 1.0

    # 3. tool_budget_reasonable (25%)
    exp_max = expected_plan.get("max_tool_calls", 8)
    plan_max = execution_plan.get("max_tool_calls", 8)
    exp_min_evidence = expected_plan.get("min_evidence_items", 2)
    plan_min_evidence = execution_plan.get("min_evidence_items", 2)

    # tool budget: 允许 ±50% 偏差
    if plan_max <= 0:
        budget_score = 0.0
    elif exp_max * 0.5 <= plan_max <= exp_max * 1.5:
        budget_score = 1.0
    else:
        ratio = min(plan_max / exp_max, exp_max / plan_max) if exp_max > 0 else 0.5
        budget_score = max(0.0, min(1.0, ratio))

    # min_evidence: 检查是否合理
    if exp_min_evidence > 0 and plan_min_evidence > 0:
        evidence_ratio = min(plan_min_evidence / exp_min_evidence,
                            exp_min_evidence / plan_min_evidence)
        evidence_score = max(0.0, min(1.0, evidence_ratio))
    else:
        evidence_score = 1.0

    budget_combined = (budget_score + evidence_score) / 2.0

    total_score = (
        scope_score * 0.40
        + required_score * 0.35
        + budget_combined * 0.25
    ) * 100.0

    return {
        "layer": "context_builder",
        "implemented": True,
        "score": round(total_score),
        "details": {
            "source_scope_match": round(scope_score * 100),
            "required_evidence_match": round(required_score * 100),
            "tool_budget_reasonable": round(budget_combined * 100),
            "expected_sources": sorted(exp_preferred),
            "actual_sources": sorted(plan_scope),
            "expected_required": sorted(exp_required),
            "actual_required": sorted(plan_required),
            "expected_max_tools": exp_max,
            "actual_max_tools": plan_max,
        },
    }
