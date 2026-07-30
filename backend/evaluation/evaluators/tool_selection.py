"""Layer 2 — Tool Selection evaluator (Phase 1 implemented)."""

from __future__ import annotations

from typing import Any

from evaluation.metrics import f1_score, precision, recall


def _extract_predicted_tools(trace: Any) -> list[str]:
    """Preserve call order; use unique set only for set metrics.

    trace 可能是:
    - dict: {"steps": [{"action": {"tool": "xxx"}}, ...], ...}
    - list[dict]: [{"tool": "xxx"}, ...]  (旧格式)
    """
    tools: list[str] = []

    if isinstance(trace, dict):
        # 新格式: trace 是 dict，工具在 steps[].action.tool
        steps = trace.get("steps") or []
        for step in steps:
            if not isinstance(step, dict):
                continue
            action = step.get("action")
            if isinstance(action, dict):
                name = action.get("tool")
                if isinstance(name, str) and name:
                    tools.append(name)
        return tools

    # 旧格式: trace 是 list
    for step in trace or []:
        if not isinstance(step, dict):
            continue
        name = step.get("tool")
        if isinstance(name, str) and name:
            tools.append(name)
    return tools


def _normalize_expected_tools(raw: Any) -> list[list[str]]:
    """将 expected_tools 归一化为 list[list[str]]。

    支持两种格式:
    - 扁平 list: ["github_search", "github_project_profile"] → 单路径
    - 嵌套 list: [["github_search", "github_project_profile"], ["web_search", "webpage_reader"]]
      → 多路径，任意一条命中即可
    """
    if not raw:
        return [[]]
    if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], list):
        # 多路径格式
        return [list(path) for path in raw]
    # 单路径格式
    return [list(raw)]


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

    支持多路径评估：如果 expected_tools 是嵌套 list，取 F1 最高的路径。

    Metrics:
    - Tool Precision
    - Tool Recall
    - Missed tools / Extra tools
    - Tool Call Order
    """
    all_paths = _normalize_expected_tools(item.get("expected_tools"))
    predicted_list = _extract_predicted_tools(trace)
    predicted_set = set(predicted_list)

    # 多路径：取 F1 最高的路径
    best_f1 = -1.0
    best_result = None

    for path in all_paths:
        path_set = set(path)
        prec = precision(predicted_set, path_set)
        rec = recall(predicted_set, path_set)
        f1 = f1_score(prec, rec)

        if f1 > best_f1:
            best_f1 = f1
            missed = sorted(path_set - predicted_set)
            extra = sorted(predicted_set - path_set)
            order = _order_score(predicted_list, path)
            best_result = {
                "precision": prec,
                "recall": rec,
                "f1": f1,
                "order": order,
                "expected_tools": path,
                "missed_tools": missed,
                "extra_tools": extra,
            }

    return {
        "layer": "tool_selection",
        "implemented": True,
        "score": {
            "precision": best_result["precision"],
            "recall": best_result["recall"],
            "f1": best_result["f1"],
            "order": best_result["order"],
        },
        "details": {
            "expected_tools": best_result["expected_tools"],
            "all_expected_paths": all_paths,
            "predicted_tools": predicted_list,
            "predicted_unique": sorted(predicted_set),
            "missed_tools": best_result["missed_tools"],
            "extra_tools": best_result["extra_tools"],
            "duplicate_calls": len(predicted_list) - len(predicted_set),
        },
    }
