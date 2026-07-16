"""Layer 2 — Tool Selection evaluator (Phase 1 implemented)."""

from __future__ import annotations

from typing import Any

from evaluation.metrics import f1_score, precision, recall


def _extract_predicted_tools(trace: list[dict[str, Any]]) -> list[str]:
    """Preserve call order; use unique set only for set metrics."""
    tools: list[str] = []
    for step in trace or []:
        name = step.get("tool")
        if isinstance(name, str) and name:
            tools.append(name)
    return tools


def _order_score(predicted: list[str], expected: list[str]) -> float:
    """
    Score whether expected tools appear in the expected relative order
    among the tools that were actually called.

    Returns 1.0 if the expected sequence is a subsequence of predicted,
    otherwise the fraction of consecutive expected pairs that preserve order.
    """
    if not expected:
        return 1.0
    if not predicted:
        return 0.0

    # Subsequence check
    i = 0
    for tool in predicted:
        if i < len(expected) and tool == expected[i]:
            i += 1
    if i == len(expected):
        return 1.0

    # Fallback: pairwise order among expected tools that were called
    predicted_index = {tool: idx for idx, tool in enumerate(predicted)}
    present = [tool for tool in expected if tool in predicted_index]
    if len(present) <= 1:
        return 0.0 if len(expected) > 1 and not present else float(len(present) > 0)

    correct_pairs = 0
    total_pairs = 0
    for left in range(len(present)):
        for right in range(left + 1, len(present)):
            total_pairs += 1
            if predicted_index[present[left]] < predicted_index[present[right]]:
                correct_pairs += 1

    return correct_pairs / total_pairs if total_pairs else 0.0


def evaluate_tool_selection(
    item: dict[str, Any],
    answer: str,
    trace: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Evaluate tool selection quality against dataset expected_tools.

    Metrics:
    - Tool Precision
    - Tool Recall
    - Missed tools / Extra tools
    - Tool Call Order
    """
    expected_list = list(item.get("expected_tools") or [])
    predicted_list = _extract_predicted_tools(trace)

    expected_set = set(expected_list)
    predicted_set = set(predicted_list)

    prec = precision(predicted_set, expected_set)
    rec = recall(predicted_set, expected_set)
    missed = sorted(expected_set - predicted_set)
    extra = sorted(predicted_set - expected_set)
    order = _order_score(predicted_list, expected_list)

    return {
        "layer": "tool_selection",
        "implemented": True,
        "score": {
            "precision": prec,
            "recall": rec,
            "f1": f1_score(prec, rec),
            "order": order,
        },
        "details": {
            "expected_tools": expected_list,
            "predicted_tools": predicted_list,
            "predicted_unique": sorted(predicted_set),
            "missed_tools": missed,
            "extra_tools": extra,
            "duplicate_calls": len(predicted_list) - len(predicted_set),
        },
    }
