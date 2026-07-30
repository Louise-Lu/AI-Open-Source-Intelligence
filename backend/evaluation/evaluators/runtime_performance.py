"""Runtime Performance Evaluator.

记录各阶段延迟和成本估算。

输出:
- total_latency
- phase_latencies (intent / context_builder / agent / final_generation)
- tool_call_count
- estimated_cost (基于 trace 中实际数据量的 token 估算)
"""

from __future__ import annotations

import json
from typing import Any


# DeepSeek 定价参考（¥ / 1M tokens）
# 输入: ¥1 / 1M tokens, 输出: ¥2 / 1M tokens
INPUT_COST_PER_TOKEN = 0.000001  # ¥1 / 1M
OUTPUT_COST_PER_TOKEN = 0.000002  # ¥2 / 1M

# 系统 prompt 基准（实际约 1500-2500 tokens）
SYSTEM_PROMPT_TOKENS = 2000


def _extract_steps(trace: Any) -> list[dict[str, Any]]:
    """从 trace 中提取步骤列表。"""
    if isinstance(trace, dict):
        for key in ("steps", "tool_trace", "tool_calls"):
            val = trace.get(key)
            if isinstance(val, list):
                return val
        return []
    elif isinstance(trace, list):
        return trace
    return []


def _count_tool_calls(trace: Any) -> int:
    """统计工具调用次数。"""
    return len(_extract_steps(trace))


def _estimate_text_tokens(text: Any) -> int:
    """估算文本的 token 数。

    中英文混合场景下，平均约 2 字符 ≈ 1 token（比纯英文的 4 字符更保守）。
    """
    if text is None:
        return 0
    if isinstance(text, str):
        return max(1, len(text) // 2)
    # dict / list → JSON 序列化后估算
    try:
        serialized = json.dumps(text, ensure_ascii=False)
        return max(1, len(serialized) // 2)
    except (TypeError, ValueError):
        return max(1, len(str(text)) // 2)


def _unwrap_output(output: Any) -> Any:
    """Unwrap ToolGateway wrapper: {"result": ..., "policy_hint": ...} → inner result."""
    if isinstance(output, dict) and "result" in output and "policy_hint" in output:
        return output["result"]
    return output


def _estimate_tokens(answer: str, trace: Any) -> dict[str, int]:
    """基于 trace 中的实际数据量估算 token 使用量。

    改进点:
    - 从 trace 中读取每个工具调用的 input/output 实际大小
    - 不再使用固定平均值
    """
    steps = _extract_steps(trace)
    tool_count = len(steps)

    # 回答 token
    answer_tokens = _estimate_text_tokens(answer)

    # 从 trace 中累加工具调用的 input/output token
    tool_input_tokens = 0
    tool_output_tokens = 0
    for step in steps:
        if not isinstance(step, dict):
            continue
        # Primary format: {"tool": str, "input": dict, "output": Any}
        tool_input = step.get("input") or {}
        raw_output = step.get("output")

        # Legacy format fallback
        if not tool_input:
            action = step.get("action")
            if isinstance(action, dict):
                tool_input = action.get("input") or {}
                raw_output = step.get("raw_output") or step.get("observation")

        tool_input_tokens += _estimate_text_tokens(tool_input)
        tool_output_tokens += _estimate_text_tokens(_unwrap_output(raw_output))

    # LLM 调用次数估算:
    # 1 (intent) + 1 (entity resolution) + 1 (plan) + tool_count (agent per step) + 1 (final answer)
    llm_calls = tool_count + 4
    # 每轮 LLM 调用都带系统 prompt + 历史对话（线性增长）
    # 平均历史长度约 llm_calls / 2 轮
    avg_history_tokens = SYSTEM_PROMPT_TOKENS + (llm_calls // 2) * 300
    llm_overhead_tokens = llm_calls * avg_history_tokens

    total_input = SYSTEM_PROMPT_TOKENS + tool_input_tokens + llm_overhead_tokens
    total_output = answer_tokens + tool_output_tokens + llm_calls * 400

    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "estimated_llm_calls": llm_calls,
        "tool_input_tokens": tool_input_tokens,
        "tool_output_tokens": tool_output_tokens,
    }


def evaluate_runtime_performance(
    case: dict[str, Any],
    total_latency: float,
    trace: Any,
    answer: str,
    phase_timings: dict[str, float] | None = None,
) -> dict[str, Any]:
    """评估运行时性能。

    Args:
        case: 评测用例
        total_latency: 总延迟（秒）
        trace: Agent 的完整 trace
        answer: 最终回答
        phase_timings: 各阶段延迟（如果可用）

    Returns:
        评估结果 dict
    """
    phase_timings = phase_timings or {}
    tool_count = _count_tool_calls(trace)
    token_info = _estimate_tokens(answer, trace)

    # 成本估算
    estimated_cost = (
        token_info["input_tokens"] * INPUT_COST_PER_TOKEN
        + token_info["output_tokens"] * OUTPUT_COST_PER_TOKEN
    )

    # 效率评估: 是否在约束范围内完成
    expected_plan = case.get("expected_plan") or {}
    max_tool_calls = expected_plan.get("max_tool_calls", 15)
    tool_budget_ok = tool_count <= max_tool_calls

    # 延迟评估: 基于工具调用次数的合理延迟
    # 每次工具调用约 3-8 秒（含网络延迟）
    expected_latency_per_call = 5.0
    expected_total = max(10.0, tool_count * expected_latency_per_call + 5.0)
    latency_ratio = total_latency / expected_total if expected_total > 0 else 1.0

    if latency_ratio <= 1.2:
        latency_rating = "fast"
    elif latency_ratio <= 2.0:
        latency_rating = "normal"
    else:
        latency_rating = "slow"

    return {
        "layer": "runtime_performance",
        "implemented": True,
        "score": round(max(0, min(100, 100 - max(0, latency_ratio - 1.0) * 30))),
        "details": {
            "total_latency": round(total_latency, 2),
            "latency_rating": latency_rating,
            "phase_timings": {
                "intent_latency": phase_timings.get("intent", 0.0),
                "context_builder_latency": phase_timings.get("context_builder", 0.0),
                "agent_latency": phase_timings.get("agent", total_latency),
                "final_generation_latency": phase_timings.get("final_generation", 0.0),
            },
            "tool_call_count": tool_count,
            "tool_budget_ok": tool_budget_ok,
            "max_tool_calls_limit": max_tool_calls,
            "token_usage": token_info,
            "estimated_cost_yuan": round(estimated_cost, 4),
        },
    }
