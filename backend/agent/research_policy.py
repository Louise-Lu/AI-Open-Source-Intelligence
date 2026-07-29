from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from typing import Any


# 不同 objective 对应不同的 Runtime Policy。
# Runtime Policy 只控制agent边界：来源优先级、证据来源数量、Discovery 预算、总工具预算和停止条件。
OBJECTIVE_POLICY: dict[str, dict[str, Any]] = {
    "information_lookup": {
        # 来源优先级
        "preferred_sources": ["github", "official", "web"],
        # 至少几个证据来源
        "min_sources": 1,
        # 每个来源最多探索几次
        "max_discovery_per_source": 2,
        # 总工具预算
        "max_total_tool_calls": 4,
        # 停止条件
        "stop_when": "对象已经能够准确介绍，没有明显信息缺口。",
    },
    "evaluation": {
        "preferred_sources": ["github", "community", "web"],
        "min_sources": 2,
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 6,
        "stop_when": "已经能够评价优缺点，并有至少两个来源相互印证。",
    },
    "comparison": {
        "preferred_sources": ["github", "community", "web"],
        "min_sources": 2,
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 8,
        "stop_when": "已经能够比较主要差异，并形成结论。",
    },
    "trend_analysis": {
        "preferred_sources": ["community", "github", "web"],
        "min_sources": 3,
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 15,
        "stop_when": "已经能够解释趋势，并有多个来源支撑。",
    },
    "technology_research": {
        "preferred_sources": ["github", "official", "web"],
        "min_sources": 2,
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 8,
        "stop_when": "已经能够解释技术原理、架构和适用场景。",
    },
    "market_research": {
        "preferred_sources": ["community", "web", "official"],
        "min_sources": 3,
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 18,
        "stop_when": "已经能够形成市场机会分析。",
    },
    "decision_support": {
        "preferred_sources": ["github", "community", "web"],
        "min_sources": 3,
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 18,
        "stop_when": "已经能够给出推荐意见，并解释原因。",
    },
}

# 若识别不到 objective，则用 default_policy
DEFAULT_POLICY: dict[str, Any] = {
    "preferred_sources": ["web", "github"],
    "min_sources": 2,
    "max_discovery_per_source": 2,
    "max_total_tool_calls": 6,
    "stop_when": "已经能够回答用户问题，并且没有明显信息缺口。",
}


# Discovery Tool：“Discovery资源”的检查和配对。
DISCOVERY_TOOL_SOURCE: dict[str, str] = {
    "github_search": "github",
    "huggingface_search": "huggingface",
    "community_search": "community",
    "youtube_search": "youtube",
    "web_search": "web",
}


# Evidence / Capability Tool：“读取证据”的检查和配对。
CAPABILITY_TOOL_SOURCE: dict[str, str] = {
    "github_project_profile": "github",
    "github_project_health": "github",
    "github_release_summary": "github",
    "github_ecosystem": "github",
    "huggingface_model_profile": "huggingface",
    "community_reader": "community",
    "webpage_reader": "web",
    "rss_reader": "web",
    "youtube_transcript": "youtube",
    "podcast_transcript": "youtube",
}


# 发现资源后，提示 Agent 应该转去用这些 Evidence Tool。
CAPABILITY_TOOLS_BY_SOURCE: dict[str, list[str]] = {
    "github": [
        "github_project_profile",
        "github_project_health",
        "github_release_summary",
        "github_ecosystem",
    ],
    "huggingface": ["huggingface_model_profile"],
    "community": ["community_reader"],
    "web": ["webpage_reader"],
    "youtube": ["youtube_transcript", "podcast_transcript"],
}


# policy_state: 当前研究状态。ContextVar 可以避免不同请求之间互相污染。
_policy_state: ContextVar[dict[str, Any] | None] = ContextVar(
    "research_policy_state",
    default=None,
)

# 初始化 policy_state
def start_research_policy(context_or_objective: Any) -> None:
    """开始一次研究时调用：优先从 ResearchContext.execution_plan 初始化 runtime policy。"""
    objective = str(getattr(context_or_objective, "objective", context_or_objective))
    execution_plan = getattr(context_or_objective, "execution_plan", None)
    policy = _policy_from_execution_plan(execution_plan)
    if policy is None:
        policy = deepcopy(OBJECTIVE_POLICY.get(objective, DEFAULT_POLICY))
    _policy_state.set(
        {
            "objective": objective,
            "policy": policy,
            "last_discovery_source": None,
            # 相同的 Discovery 的次数
            "same_discovery_count": 0,
            # Discovery 的次数
            "discovery_counts": {},      # 例：{"github": 1}
            "discovered_resources": {},  # 例：{"github": ["owner/repo"]}
            "evidence_sources": [],      # 例：["github", "community"]
            "tool_calls": 0,
            "reader_counts": {},
        }
    )


def _policy_from_execution_plan(execution_plan: Any) -> dict[str, Any] | None:
    """把 ExecutionPlan 转成 Runtime Policy；没有 plan 时返回 None。"""
    if not execution_plan:
        return None

    if hasattr(execution_plan, "model_dump"):
        plan = execution_plan.model_dump()
    elif isinstance(execution_plan, dict):
        plan = execution_plan
    else:
        return None

    source_scope = [str(source) for source in plan.get("source_scope", []) or []]
    required_sources = [str(source) for source in plan.get("required_sources", []) or []]
    avoid_sources = [str(source) for source in plan.get("avoid_sources", []) or []]
    if not source_scope:
        return None

    return {
        "preferred_sources": source_scope,
        "required_sources": required_sources,
        "avoid_sources": avoid_sources,
        "allowed_tools": [str(tool) for tool in plan.get("allowed_tools", []) or []],
        "blocked_tools": [str(tool) for tool in plan.get("blocked_tools", []) or []],
        "min_sources": max(1, len(required_sources) or min(2, len(source_scope))),
        "max_discovery_per_source": int(plan.get("max_discovery_per_source", 1) or 1),
        "max_reader_per_source": int(plan.get("max_reader_per_source", 1) or 1),
        "max_total_tool_calls": int(plan.get("max_tool_calls", 6) or 6),
        "stop_when": str(plan.get("stop_when") or "required_sources_satisfied"),
    }

# 结束后清空 policy_state
def clear_research_policy() -> None:
    """研究结束后清空状态。"""
    _policy_state.set(None)


# 构建 当前的 policy_hit 
# 当前的 policy_state -> 生成 给 LLM 看的自然语言提示 {policy hint} 
#                    -> 终端看
def build_policy_hint() -> str:
    """生成给 LLM 看的自然语言提示policy hint"""
    state = _policy_state.get() or {}

    policy: dict[str, Any] = state.get("policy", DEFAULT_POLICY)
    objective = str(state.get("objective", "unknown"))
    discovery_counts: dict[str, int] = state.get("discovery_counts", {}) or {}
    evidence_sources: list[str] = state.get("evidence_sources", []) or []
    tool_calls = int(state.get("tool_calls", 0))
    max_total_tool_calls = int(policy["max_total_tool_calls"])
    required_sources = policy.get("required_sources", []) or []
    avoid_sources = policy.get("avoid_sources", []) or []
    allowed_tools = policy.get("allowed_tools", []) or []
    blocked_tools = policy.get("blocked_tools", []) or []
    evidence_count = len(set(evidence_sources))
    status = (
        "Ready to Finish - stop calling tools and write final answer"
        if state and _is_ready_to_finish(state)
        else "Continue Research"
    )

    preferred_sources = "\n".join(_label(source) for source in policy["preferred_sources"])
    progress = "\n".join(
        f"{_label(source)}:{int(discovery_counts.get(source, 0))}"
        for source in policy["preferred_sources"]
    )
    evidence = _evidence_sources_text(evidence_sources)

    return (
        "当前 Research Policy: \n"
        f"Objective:{objective}\n"
        "Preferred Sources: \n"
        f"{preferred_sources}\n"
        "Minimum Evidence Sources:"
        f"{policy['min_sources']}\n"
        "Required Evidence Sources:"
        f"{', '.join(_label(s) for s in required_sources) if required_sources else 'Any'}\n"
        "Avoid Sources:"
        f"{', '.join(_label(s) for s in avoid_sources) if avoid_sources else 'None'}\n"
        "Allowed Tools:"
        f"{', '.join(allowed_tools) if allowed_tools else 'Any tool within allowed sources'}\n"
        "Blocked Tools:"
        f"{', '.join(blocked_tools) if blocked_tools else 'None'}\n"
        "Maximum Discovery Per Source:"
        f"{policy['max_discovery_per_source']}\n"
        "Maximum Reader Per Source:"
        f"{policy.get('max_reader_per_source', 1)}\n"
        "Maximum Tool Calls:"
        f"{max_total_tool_calls}\n"
        "Stopping Condition:"
        f"{policy['stop_when']}\n\n"
        
        "Current Progress\n"
        f"{progress}\n"
        "Tool Calls:"
        f"{tool_calls}/{max_total_tool_calls}\n"
        "Evidence Sources:\n"
        f"{evidence}\n"
        "Status:"
        f"{status}"
    )


def _is_ready_to_finish(state: dict[str, Any]) -> bool:
    """判断当前研究是否已经满足 Runtime Policy 的停止条件。"""
    policy: dict[str, Any] = state["policy"]
    evidence_sources: list[str] = state.get("evidence_sources", []) or []
    tool_calls = int(state.get("tool_calls", 0))
    required_sources: list[str] = policy.get("required_sources", []) or []
    if required_sources and set(required_sources).issubset(set(evidence_sources)):
        return True
    return (
        tool_calls >= int(policy["max_total_tool_calls"])
        or len(set(evidence_sources)) >= int(policy["min_sources"])
    )

# before_tool_call 检查 policy_state 2处：
    # 这个discovery来源是否已经发现过资源，如果发现过，就不应该继续 search，而应该去读 evidence。
    # 这个discovery来源是否已经超过 max_discovery_per_source。
def before_tool_call(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any] | None:
    """Tool 调用前检查：是否应该阻止这次工具调用。"""
    state = _policy_state.get()

    if not state:
        return None

    source = (
        DISCOVERY_TOOL_SOURCE.get(tool_name)
        or CAPABILITY_TOOL_SOURCE.get(tool_name)
        or "unknown"
    )
    policy: dict[str, Any] = state["policy"]

    blocked_tools = set(policy.get("blocked_tools", []) or [])
    if tool_name in blocked_tools:
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"{tool_name} 在本次执行计划的工具黑名单中。",
            suggestion=f"请只使用允许工具: {', '.join(policy.get('allowed_tools', []) or []) or '当前允许来源内的工具'}。",
            tool_input=tool_input,
        )

    allowed_tools = set(policy.get("allowed_tools", []) or [])
    if allowed_tools and tool_name not in allowed_tools:
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"{tool_name} 不在本次执行计划的工具白名单中。",
            suggestion=f"请切换到允许工具: {', '.join(sorted(allowed_tools))}。",
            tool_input=tool_input,
        )

    if source in set(policy.get("avoid_sources", []) or []):
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"{_label(source)} 不在本次执行计划范围内。",
            suggestion=f"请只使用允许来源: {', '.join(_label(s) for s in policy.get('preferred_sources', []))}。",
            tool_input=tool_input,
        )

    allowed_sources = set(policy.get("preferred_sources", []) or [])
    if source != "unknown" and allowed_sources and source not in allowed_sources:
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"{_label(source)} 不在本次允许的数据源范围内。",
            suggestion=f"请切换到允许来源: {', '.join(_label(s) for s in allowed_sources)}。",
            tool_input=tool_input,
        )

    if _is_ready_to_finish(state):
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason="当前研究已经满足 Runtime Policy 的停止条件。",
            suggestion="建议停止继续搜索，基于已有证据生成结论。",
            tool_input=tool_input,
        )

    if int(state.get("tool_calls", 0)) >= int(policy["max_total_tool_calls"]):
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"工具调用次数已经达到上限 {policy['max_total_tool_calls']}。",
            suggestion="建议停止继续搜索，基于已有证据生成结论。",
            tool_input=tool_input,
        )

    if tool_name not in DISCOVERY_TOOL_SOURCE:
        reader_count = int(state.get("reader_counts", {}).get(source, 0))
        if reader_count >= int(policy.get("max_reader_per_source", 1)):
            return _policy_block(
                tool_name=tool_name,
                source=source,
                reason=f"{_label(source)} Evidence Reader 已调用 {reader_count} 次。",
                suggestion="请停止继续读取同一来源，基于已有证据生成结论。",
                tool_input=tool_input,
            )
        return None

    # 规则 1：同一个 Discovery 来源调用太多次，就要求切换来源。
    discovery_count = int(state.get("discovery_counts", {}).get(source, 0))
    if discovery_count >= int(policy["max_discovery_per_source"]):
        alternatives = [s for s in policy["preferred_sources"] if s != source]
        discovered = state.get("discovered_resources", {}).get(source, [])
        tools = CAPABILITY_TOOLS_BY_SOURCE.get(source, [])
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"{_label(source)} 已探索 {policy['max_discovery_per_source']} 次。",
            suggestion=(
                f"建议切换到: {', '.join(_label(s) for s in alternatives)}。"
                f"如果已发现资源，优先调用 Evidence Tool: {', '.join(tools)}。"
                f"已发现资源: {discovered[:3]}"
            ),
            tool_input=tool_input,
        )

    return None

# after_tool_call 更新 policy_state 3处：
    # Discovery计数 discovery_counts, 
    # 已发现资源 discovered_resources,
    # 已获得证据来源 evidence_sources
def after_tool_call(tool_name: str, tool_output: Any) -> None:
    """Tool 调用后更新状态：Discovery 计数、已发现资源、已获得证据来源。"""
    state = _policy_state.get()
    if not state:
        return

    state["tool_calls"] = int(state.get("tool_calls", 0)) + 1

    if tool_name in DISCOVERY_TOOL_SOURCE:
        _record_discovery(state, tool_name, tool_output)
        return

    if tool_name in CAPABILITY_TOOL_SOURCE:
        source = CAPABILITY_TOOL_SOURCE[tool_name]
        reader_counts = state.setdefault("reader_counts", {})
        reader_counts[source] = int(reader_counts.get(source, 0)) + 1
        evidence_sources = state.setdefault("evidence_sources", [])
        if source not in evidence_sources:
            evidence_sources.append(source)


def sync_research_policy_from_trace(trace: list[dict[str, Any]]) -> None:
    """如果工具在其它执行上下文里运行，用 trace 重新同步 policy_state。"""
    state = _policy_state.get()
    if not state:
        return

    state.update(
        {
            "last_discovery_source": None,
            "same_discovery_count": 0,
            "discovery_counts": {},
            "discovered_resources": {},
            "evidence_sources": [],
            "tool_calls": 0,
            "reader_counts": {},
        }
    )

    for item in trace:
        # 兼容 Tool Observation 包装结构，只取原始 result
        output = item.get("output")
        if isinstance(output, dict) and "result" in output and "policy_hint" in output:
            output = output.get("result")
        after_tool_call(str(item.get("tool", "")), output)

# 趋势分析如果只有 GitHub 证据，需要提醒用户证据不足
def needs_trend_single_source_warning() -> bool:
    """趋势分析如果只有 GitHub 证据，需要提醒用户证据不足。"""
    state = _policy_state.get()
    if not state or state.get("objective") != "trend_analysis":
        return False
    return set(state.get("evidence_sources", [])) == {"github"}


# --------- build_policy_hint() -------------
## 构建 Current Progress 的 label： 即 discovery 的名称
def _label(source: str) -> str:
    """把内部 source 名称转成给 LLM 看的名称。"""
    return {
        "github": "GitHub",
        "web": "Web",
        "community": "Community",
        "youtube": "YouTube",
        "huggingface": "HuggingFace",
        "official": "Official",
    }.get(source, source)

## 构建 Evidence Sources
def _evidence_sources_text(evidence_sources: list[str]) -> str:
    if not evidence_sources:
        return "None"
    return "\n".join(_label(source) for source in sorted(set(evidence_sources)))


# --------- before_tool_call() -------------
# 返回给 LLM 的 policy 拦截信息
def _policy_block(
    *,
    tool_name: str,
    source: str,
    reason: str,
    suggestion: str,
    tool_input: dict[str, Any],
) -> dict[str, Any]:
    """返回给 LLM 的 policy 拦截信息。"""
    return {
        "source": "research_policy",
        "type": "tool_policy_block",
        "summary": f"ResearchPolicy 阻止了 {tool_name} 调用。",
        "evidence": {
            "blocked_tool": tool_name,
            "blocked_source": source,
            "input": tool_input,
            "reason": reason,
            "suggestion": suggestion,
        },
    }


# --------- after_tool_call() -------------
# 更新 policy_state 的三块地方：
#   last_discovery_source / same_discovery_count
#   discovery_counts
#   discovered_resources（从 tool_output 里提取 identifier）
def _record_discovery(state: dict[str, Any], tool_name: str, tool_output: Any) -> None:
    """记录一次 Discovery Tool 调用：更新计数 + 提取已发现资源。

    重要：如果 Discovery 返回空结果，不计入 discovery_counts，
    让 Agent 有机会换关键词重试。
    """
    source = DISCOVERY_TOOL_SOURCE[tool_name]

    # 1. 兼容 Tool Observation 包装结构，只取原始 result
    unwrapped = tool_output
    if isinstance(unwrapped, dict) and "result" in unwrapped and "policy_hint" in unwrapped:
        unwrapped = unwrapped.get("result")

    # 2. 从 DiscoveryResult 列表里提取 identifier，更新 discovered_resources
    found_identifiers: list[str] = []
    if isinstance(unwrapped, list):
        discovered = state.setdefault("discovered_resources", {})
        existing = discovered.setdefault(source, [])
        for item in unwrapped:
            if isinstance(item, dict) and item.get("identifier"):
                identifier = str(item["identifier"])
                if identifier not in existing:
                    existing.append(identifier)
                found_identifiers.append(identifier)

    # 3. 只有发现了资源才计入 discovery_counts，空结果不消耗 discovery 预算
    if not found_identifiers:
        return

    if state.get("last_discovery_source") == source:
        state["same_discovery_count"] = int(state.get("same_discovery_count", 0)) + 1
    else:
        state["last_discovery_source"] = source
        state["same_discovery_count"] = 1

    counts = state.setdefault("discovery_counts", {})
    counts[source] = int(counts.get(source, 0)) + 1
