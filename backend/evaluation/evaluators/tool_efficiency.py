"""Tool Efficiency Evaluator.
评估 Agent 工具调用的效率和质量 

核心指标:
1. Tool Precision — 有效工具调用占比 (useful_calls / total_calls)
2. Source Recall — 必需来源的覆盖率 (covered_required / required_evidence)
3. Parameter Accuracy — 工具参数是否正确（搜索词是否包含目标实体）
4. F1 — Precision 和 Recall 的调和平均

统计输出:
- total_tool_calls / discovery_calls / reader_calls / blocked_calls
- called_sources / expected_sources / missing_sources
- parameter_checks — 每个 discovery 工具的参数检查结果

综合分 = precision * 40 + recall * 40 + param_accuracy * 20 (0-100)
"""

from __future__ import annotations

from typing import Any


# Discovery tools
DISCOVERY_TOOLS = {
    "github_search", "huggingface_search", "community_search",
    "web_search", "youtube_search",
}

# Evidence / Reader tools
READER_TOOLS = {
    "github_project_profile", "github_project_health",
    "github_release_summary", "github_ecosystem",
    "huggingface_model_profile",
    "community_reader", "webpage_reader",
    "youtube_transcript", "podcast_transcript", "rss_reader",
}

# Tool → source mapping
TOOL_SOURCE: dict[str, str] = {
    "github_search": "github",
    "github_project_profile": "github",
    "github_project_health": "github",
    "github_release_summary": "github",
    "github_ecosystem": "github",
    "huggingface_search": "huggingface",
    "huggingface_model_profile": "huggingface",
    "community_search": "community",
    "community_reader": "community",
    "web_search": "web",
    "webpage_reader": "web",
    "rss_reader": "web",
    "youtube_search": "youtube",
    "youtube_transcript": "youtube",
    "podcast_transcript": "youtube",
}


def _extract_tool_trace(trace: Any) -> list[dict[str, Any]]:
    """从 trace 中提取工具调用列表。

    trace 格式 (agent/trace.py):
      {"tool": str, "input": dict, "output": Any}
    """
    tools: list[dict[str, Any]] = []

    if isinstance(trace, dict):
        for key in ("steps", "tool_trace", "tool_calls"):
            val = trace.get(key)
            if isinstance(val, list):
                steps = val
                break
        else:
            steps = []
    elif isinstance(trace, list):
        steps = trace
    else:
        return tools

    for step in steps:
        if not isinstance(step, dict):
            continue

        # 当前格式: {"tool": str, "input": dict, "output": Any}
        name = step.get("tool", "")
        tool_input = step.get("input") or {}
        output = step.get("output") or ""

        if name:
            tools.append({
                "tool": name,
                "input": tool_input,
                "output": output,
                "source": TOOL_SOURCE.get(name, "unknown"),
            })
    return tools


def _is_blocked_call(tool_name: str, output: Any) -> bool:
    """检查工具调用是否被 policy 阻止。"""
    if isinstance(output, str) and "tool_policy_block" in output:
        return True
    if isinstance(output, dict) and output.get("blocked"):
        return True
    return False


def _is_useful_call(call: dict[str, Any], output: Any) -> bool:
    """判断工具调用是否有效（产出了有用结果）。"""
    tool_name = call["tool"]
    source = call["source"]

    # 被 policy 阻止的调用不算有效
    if _is_blocked_call(tool_name, output):
        return False

    # Discovery 工具：返回非空结果算有效
    if tool_name in DISCOVERY_TOOLS:
        if isinstance(output, list):
            return len(output) > 0
        if isinstance(output, str):
            return bool(output.strip()) and "no result" not in output.lower()
        return output is not None

    # Reader 工具：返回非空 evidence 算有效
    if tool_name in READER_TOOLS:
        if isinstance(output, dict):
            evidence = output.get("evidence") or output
            return bool(evidence)
        if isinstance(output, str):
            return bool(output.strip())
        return output is not None

    # 未知工具：有输出就算有效
    return output is not None


def _extract_called_sources(tool_trace: list[dict[str, Any]]) -> set[str]:
    """提取实际调用的来源集合。"""
    sources: set[str] = set()
    for call in tool_trace:
        source = call.get("source", "unknown")
        if source != "unknown":
            sources.add(source)
    return sources


def _check_tool_parameters(
    tool_trace: list[dict[str, Any]],
    case: dict[str, Any],
) -> tuple[int, int, list[dict[str, Any]]]:
    """检查 discovery 工具的参数是否正确（搜索词是否包含目标实体）。

    Returns:
        (total_params, correct_params, check_details)
    """
    expected_intent = case.get("expected_intent") or {}
    entities = expected_intent.get("entities") or []
    entity_lower = {e.lower() for e in entities if e}

    if not entity_lower:
        return 0, 0, []

    total = 0
    correct = 0
    checks: list[dict[str, Any]] = []

    for call in tool_trace:
        if call["tool"] not in DISCOVERY_TOOLS:
            continue

        tool_input = call.get("input") or {}
        # 提取搜索关键词（不同工具的参数名可能不同）
        query = ""
        for key in ("query", "keyword", "search_term", "name", "repo"):
            val = tool_input.get(key)
            if isinstance(val, str) and val:
                query = val
                break

        if not query:
            continue

        total += 1
        query_lower = query.lower()
        # 检查搜索词是否包含至少一个目标实体
        matched = any(ent in query_lower for ent in entity_lower)
        if matched:
            correct += 1

        checks.append({
            "tool": call["tool"],
            "query": query[:80],
            "matched": matched,
        })

    return total, correct, checks


def evaluate_tool_efficiency(
    case: dict[str, Any],
    trace: Any,
) -> dict[str, Any]:
    """评估工具调用效率。

    Args:
        case: 评测用例
        trace: Agent 的完整 trace

    Returns:
        评估结果 dict
    """
    tool_trace = _extract_tool_trace(trace)
    total = len(tool_trace)

    if total == 0:
        return {
            "layer": "tool_efficiency",
            "implemented": True,
            "score": 0,
            "details": {
                "total_tool_calls": 0,
                "discovery_calls": 0,
                "reader_calls": 0,
                "blocked_calls": 0,
                "useful_calls": 0,
                "tool_precision": 0.0,
                "source_recall": 0.0,
                "parameter_accuracy": 0.0,
                "called_sources": [],
            },
        }

    discovery_count = 0
    reader_count = 0
    blocked_count = 0
    useful_count = 0

    for call in tool_trace:
        tool_name = call["tool"]
        output = call["output"]

        if tool_name in DISCOVERY_TOOLS:
            discovery_count += 1
        elif tool_name in READER_TOOLS:
            reader_count += 1

        if _is_blocked_call(tool_name, output):
            blocked_count += 1
        elif _is_useful_call(call, output):
            useful_count += 1

    # ── 1. Tool Precision: 有效调用占比 ──
    tool_precision = useful_count / total if total > 0 else 0.0

    # ── 2. Source Recall: 必需来源覆盖率 ──
    expected_plan = case.get("expected_plan") or {}
    exp_sources = set(expected_plan.get("source_scope") or [])
    required_evidence = set(expected_plan.get("required_evidence") or [])
    called_sources = _extract_called_sources(tool_trace)

    if required_evidence:
        source_recall = len(required_evidence & called_sources) / len(required_evidence)
    elif exp_sources:
        source_recall = len(exp_sources & called_sources) / len(exp_sources)
    else:
        source_recall = 1.0

    # ── 3. Parameter Accuracy: 搜索参数是否正确 ──
    total_params, correct_params, param_checks = _check_tool_parameters(tool_trace, case)
    param_accuracy = correct_params / total_params if total_params > 0 else 1.0

    # ── 4. F1 (Precision vs Recall) ──
    if tool_precision + source_recall > 0:
        f1 = 2 * tool_precision * source_recall / (tool_precision + source_recall)
    else:
        f1 = 0.0

    # ── 综合分 = precision * 40 + recall * 40 + param * 20 ──
    combined_score = (
        tool_precision * 40
        + source_recall * 40
        + param_accuracy * 20
    )

    return {
        "layer": "tool_efficiency",
        "implemented": True,
        "score": round(combined_score),
        "details": {
            "total_tool_calls": total,
            "discovery_calls": discovery_count,
            "reader_calls": reader_count,
            "blocked_calls": blocked_count,
            "useful_calls": useful_count,
            # 三大核心指标
            "tool_precision": round(tool_precision, 3),
            "source_recall": round(source_recall, 3),
            "parameter_accuracy": round(param_accuracy, 3),
            "f1": round(f1, 3),
            # 来源覆盖
            "called_sources": sorted(called_sources),
            "expected_sources": sorted(exp_sources),
            "required_evidence": sorted(required_evidence),
            "missing_sources": sorted(required_evidence - called_sources),
            # 参数检查明细
            "parameter_checks": param_checks,
        },
    }
