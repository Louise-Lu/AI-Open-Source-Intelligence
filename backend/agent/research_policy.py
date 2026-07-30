from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from typing import Any


# 不同 objective 对应不同的 Runtime Policy 默认值。
# 如果 ExecutionPlan 存在，优先从 ExecutionPlan 初始化。
OBJECTIVE_POLICY: dict[str, dict[str, Any]] = {
    "information_lookup": {
        "preferred_sources": ["github", "official", "web"],
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 4,
        "stop_conditions": {"min_sources": 1, "min_evidence_items": 2},
    },
    "evaluation": {
        "preferred_sources": ["github", "community", "web"],
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 6,
        "stop_conditions": {"min_sources": 2, "min_evidence_items": 4},
    },
    "comparison": {
        "preferred_sources": ["github", "community", "web"],
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 8,
        "stop_conditions": {"min_sources": 2, "min_evidence_items": 4},
    },
    "trend_analysis": {
        "preferred_sources": ["community", "github", "web"],
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 15,
        "stop_conditions": {"min_sources": 3, "min_evidence_items": 4},
    },
    "technology_research": {
        "preferred_sources": ["github", "official", "web"],
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 8,
        "stop_conditions": {"min_sources": 2, "min_evidence_items": 4},
    },
    "market_research": {
        "preferred_sources": ["community", "web", "official"],
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 18,
        "stop_conditions": {"min_sources": 3, "min_evidence_items": 4},
    },
    "decision_support": {
        "preferred_sources": ["github", "community", "web"],
        "max_discovery_per_source": 2,
        "max_total_tool_calls": 18,
        "stop_conditions": {"min_sources": 3, "min_evidence_items": 4},
    },
}

DEFAULT_POLICY: dict[str, Any] = {
    "preferred_sources": ["web", "github"],
    "max_discovery_per_source": 2,
    "max_total_tool_calls": 6,
    "stop_conditions": {"min_sources": 2, "min_evidence_items": 2},
}


# Discovery Tool → source 映射
DISCOVERY_TOOL_SOURCE: dict[str, str] = {
    "github_search": "github",
    "huggingface_search": "huggingface",
    "community_search": "community",
    "youtube_search": "youtube",
    "web_search": "web",
}

# Capability / Evidence Tool → source 映射
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


# policy_state: 当前研究状态。ContextVar 避免不同请求之间互相污染。
_policy_state: ContextVar[dict[str, Any] | None] = ContextVar(
    "research_policy_state",
    default=None,
)


def start_research_policy(plan: Any) -> None:
    """开始一次研究时调用：从 ExecutionPlan 初始化 runtime policy。"""
    objective = str(getattr(plan, "objective", "unknown"))
    policy = _policy_from_execution_plan(plan)
    if policy is None:
        policy = deepcopy(OBJECTIVE_POLICY.get(objective, DEFAULT_POLICY))
    _policy_state.set(
        {
            "objective": objective,
            "policy": policy,
            "last_discovery_source": None,
            "same_discovery_count": 0,
            "discovery_counts": {},
            "empty_discovery_counts": {},   # 每个来源空结果计数
            "discovered_resources": {},
            "evidence_sources": [],
            "evidence_items": 0,            # 已收集的证据条目总数
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

    source_scope = [str(s) for s in plan.get("source_scope", []) or []]
    required_evidence = [str(s) for s in plan.get("required_evidence", []) or []]
    avoid_sources = [str(s) for s in plan.get("avoid_sources", []) or []]
    if not source_scope:
        return None

    # 从 stop_conditions 读取停止条件
    stop_conditions = plan.get("stop_conditions") or {}
    if isinstance(stop_conditions, dict):
        min_sources = int(stop_conditions.get("min_sources", 1) or 1)
        min_evidence_items_from_stop = int(stop_conditions.get("min_evidence_items", 2) or 2)
    else:
        min_sources = 1
        min_evidence_items_from_stop = 2

    return {
        "preferred_sources": source_scope,
        "required_evidence": required_evidence,
        "avoid_sources": avoid_sources,
        "mode": str(plan.get("mode", "standard") or "standard"),
        "min_sources": max(min_sources, len(required_evidence) or min(2, len(source_scope))),
        "min_evidence_items": int(plan.get("min_evidence_items", min_evidence_items_from_stop) or 2),
        "max_discovery_per_source": int(plan.get("max_discovery_per_source", 2) or 2),
        "max_empty_retry_per_source": int(plan.get("max_empty_retry_per_source", 1) or 1),
        "max_reader_per_source": int(plan.get("max_reader_per_source", 2) or 2),
        "max_evidence_items": int(plan.get("max_evidence_items", 10) or 10),
        "max_total_tool_calls": int(plan.get("max_tool_calls", 8) or 8),
        "stop_conditions": {
            "min_sources": min_sources,
            "min_evidence_items": min_evidence_items_from_stop,
        },
    }


def clear_research_policy() -> None:
    """研究结束后清空状态。"""
    _policy_state.set(None)


# ─────────────────────────────────────────────────────────
# policy_hint — 给 LLM 看的自然语言提示
# ─────────────────────────────────────────────────────────

def build_policy_hint() -> str:
    """生成给 LLM 看的 Current Research Policy 提示。"""
    state = _policy_state.get() or {}

    policy: dict[str, Any] = state.get("policy", DEFAULT_POLICY)
    objective = str(state.get("objective", "unknown"))
    discovery_counts: dict[str, int] = state.get("discovery_counts", {}) or {}
    evidence_sources: list[str] = state.get("evidence_sources", []) or []
    evidence_items: int = int(state.get("evidence_items", 0))
    tool_calls = int(state.get("tool_calls", 0))
    max_total_tool_calls = int(policy.get("max_total_tool_calls", 8))
    required_evidence = policy.get("required_evidence", []) or []
    min_evidence_items = int(policy.get("min_evidence_items", 2))
    max_evidence_items = int(policy.get("max_evidence_items", 10))
    stop_conditions = policy.get("stop_conditions", {}) or {}
    min_sources = int(stop_conditions.get("min_sources", 1))
    status = (
        "Ready to Finish - stop calling tools and write final answer"
        if state and _is_ready_to_finish(state)
        else "Continue Research"
    )

    preferred_sources_text = "\n".join(
        f"  - {_label(s)}" for s in policy.get("preferred_sources", [])
    )
    evidence_needed = (
        f"Required Evidence: {', '.join(_label(s) for s in required_evidence) or 'Any'}\n"
        f"  Min Evidence Items: {min_evidence_items}\n"
        f"  Max Evidence Items: {max_evidence_items}"
    )
    budget = (
        f"Max Discovery Per Source: {policy.get('max_discovery_per_source', 2)}\n"
        f"  Max Empty Retry Per Source: {policy.get('max_empty_retry_per_source', 1)}\n"
        f"  Max Reader Per Source: {policy.get('max_reader_per_source', 2)}\n"
        f"  Max Tool Calls: {max_total_tool_calls}"
    )
    collected = (
        f"Sources: {', '.join(_label(s) for s in sorted(set(evidence_sources))) or 'None'}\n"
        f"  Evidence Items: {evidence_items}\n"
        f"  Tool Calls: {tool_calls}/{max_total_tool_calls}"
    )
    stop_condition_text = (
        f"  Min Sources: {min_sources}\n"
        f"  Min Evidence Items: {min_evidence_items}"
    )

    return (
        "Current Research Policy\n\n"
        f"Objective: {objective}\n\n"
        f"Preferred Sources:\n{preferred_sources_text}\n\n"
        f"Evidence Needed:\n  {evidence_needed}\n\n"
        f"Budget:\n  {budget}\n\n"
        f"Collected Evidence:\n  {collected}\n\n"
        f"Stop Conditions:\n{stop_condition_text}\n\n"
        f"Status: {status}"
    )


# ─────────────────────────────────────────────────────────
# 停止条件判断
# ─────────────────────────────────────────────────────────

def _is_ready_to_finish(state: dict[str, Any]) -> bool:
    """判断当前研究是否已经满足停止条件。

    需要同时满足：
    1. required_evidence 全部覆盖
    2. evidence_sources 数量 >= min_sources (from stop_conditions)
    3. evidence_items >= min_evidence_items
    """
    policy: dict[str, Any] = state["policy"]
    evidence_sources: list[str] = state.get("evidence_sources", []) or []
    evidence_items: int = int(state.get("evidence_items", 0))
    tool_calls = int(state.get("tool_calls", 0))
    max_total_tool_calls = int(policy.get("max_total_tool_calls", 8))

    required_evidence: list[str] = policy.get("required_evidence", []) or []
    stop_conditions: dict[str, Any] = policy.get("stop_conditions", {}) or {}
    min_sources: int = int(stop_conditions.get("min_sources", policy.get("min_sources", 1)))
    min_evidence_items: int = int(stop_conditions.get("min_evidence_items", policy.get("min_evidence_items", 2)))

    # 硬性上限：工具预算用完
    if tool_calls >= max_total_tool_calls:
        return True

    # 证据上限：已收集够多证据
    max_evidence_items: int = int(policy.get("max_evidence_items", 10))
    if evidence_items >= max_evidence_items:
        return True

    # 正常停止条件：required_evidence + min_sources + min_evidence_items 同时满足
    sources_satisfied = set(required_evidence).issubset(set(evidence_sources))
    count_satisfied = len(set(evidence_sources)) >= min_sources
    items_satisfied = evidence_items >= min_evidence_items

    return sources_satisfied and count_satisfied and items_satisfied


# ─────────────────────────────────────────────────────────
# before_tool_call — 工具调用前检查
# ─────────────────────────────────────────────────────────

def before_tool_call(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any] | None:
    """Tool 调用前检查：是否应该阻止这次工具调用。

    判断顺序：
    1. tool source 不在 source_scope 或在 avoid_sources → block
    2. 超过 tool budget → block
    """
    state = _policy_state.get()
    if not state:
        return None

    source = (
        DISCOVERY_TOOL_SOURCE.get(tool_name)
        or CAPABILITY_TOOL_SOURCE.get(tool_name)
        or "unknown"
    )
    policy: dict[str, Any] = state["policy"]

    # 1. tool source 不在 source_scope 或在 avoid_sources → block
    allowed_sources = set(policy.get("preferred_sources", []) or [])
    avoid_sources = set(policy.get("avoid_sources", []) or [])
    if source in avoid_sources:
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"{_label(source)} 不在本次执行计划范围内。",
            suggestion=f"请只使用允许来源: {', '.join(_label(s) for s in allowed_sources)}。",
            tool_input=tool_input,
        )
    if source != "unknown" and allowed_sources and source not in allowed_sources:
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"{_label(source)} 不在本次允许的数据源范围内。",
            suggestion=f"请切换到允许来源: {', '.join(_label(s) for s in allowed_sources)}。",
            tool_input=tool_input,
        )

    # 2. 超过 tool budget → block
    if _is_ready_to_finish(state):
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason="当前研究已经满足停止条件。",
            suggestion="请停止继续搜索，基于已有证据生成结论。",
            tool_input=tool_input,
        )

    if int(state.get("tool_calls", 0)) >= int(policy.get("max_total_tool_calls", 8)):
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"工具调用次数已经达到上限 {policy['max_total_tool_calls']}。",
            suggestion="请停止继续搜索，基于已有证据生成结论。",
            tool_input=tool_input,
        )

    # Discovery 工具的特殊检查
    if tool_name in DISCOVERY_TOOL_SOURCE:
        discovery_count = int(state.get("discovery_counts", {}).get(source, 0))
        empty_count = int(state.get("empty_discovery_counts", {}).get(source, 0))
        max_discovery = int(policy.get("max_discovery_per_source", 2))
        max_empty = int(policy.get("max_empty_retry_per_source", 1))

        # 总 discovery 次数（含空结果）超过上限
        if discovery_count + empty_count >= max_discovery + max_empty:
            tools = CAPABILITY_TOOLS_BY_SOURCE.get(source, [])
            return _policy_block(
                tool_name=tool_name,
                source=source,
                reason=f"{_label(source)} Discovery 已达到上限（{discovery_count} 次成功 + {empty_count} 次空结果）。",
                suggestion=f"请调用 Evidence Tool 读取已发现资源: {', '.join(tools)}。",
                tool_input=tool_input,
            )

    # Reader 工具的特殊检查
    if tool_name not in DISCOVERY_TOOL_SOURCE and source != "unknown":
        reader_count = int(state.get("reader_counts", {}).get(source, 0))
        max_reader = int(policy.get("max_reader_per_source", 2))
        if reader_count >= max_reader:
            return _policy_block(
                tool_name=tool_name,
                source=source,
                reason=f"{_label(source)} Evidence Reader 已调用 {reader_count} 次。",
                suggestion="请停止继续读取同一来源，基于已有证据生成结论。",
                tool_input=tool_input,
            )

    return None


# ─────────────────────────────────────────────────────────
# after_tool_call — 工具调用后更新状态
# ─────────────────────────────────────────────────────────

def after_tool_call(tool_name: str, tool_output: Any) -> None:
    """Tool 调用后更新状态：Discovery 计数、已发现资源、已获得证据来源。

    空结果也消耗 discovery_count。
    """
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
        # 估算 evidence_items：每次 reader 调用算 1 条证据
        state["evidence_items"] = int(state.get("evidence_items", 0)) + 1


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
            "empty_discovery_counts": {},
            "discovered_resources": {},
            "evidence_sources": [],
            "evidence_items": 0,
            "tool_calls": 0,
            "reader_counts": {},
        }
    )

    for item in trace:
        output = item.get("output")
        if isinstance(output, dict) and "result" in output and "policy_hint" in output:
            output = output.get("result")
        after_tool_call(str(item.get("tool", "")), output)


def needs_trend_single_source_warning() -> bool:
    """趋势分析如果只有 GitHub 证据，需要提醒用户证据不足。"""
    state = _policy_state.get()
    if not state or state.get("objective") != "trend_analysis":
        return False
    return set(state.get("evidence_sources", [])) == {"github"}


# ─────────────────────────────────────────────────────────
# 内部辅助函数
# ─────────────────────────────────────────────────────────

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


def _record_discovery(state: dict[str, Any], tool_name: str, tool_output: Any) -> None:
    """记录一次 Discovery Tool 调用。

    空结果也消耗 discovery 预算（通过 empty_discovery_counts 追踪）。
    """
    source = DISCOVERY_TOOL_SOURCE[tool_name]

    # 兼容 Tool Observation 包装结构
    unwrapped = tool_output
    if isinstance(unwrapped, dict) and "result" in unwrapped and "policy_hint" in unwrapped:
        unwrapped = unwrapped.get("result")

    # 从 DiscoveryResult 列表里提取 identifier
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

    if found_identifiers:
        # 有结果：计入 discovery_counts
        counts = state.setdefault("discovery_counts", {})
        counts[source] = int(counts.get(source, 0)) + 1
    else:
        # 空结果：计入 empty_discovery_counts
        empty_counts = state.setdefault("empty_discovery_counts", {})
        empty_counts[source] = int(empty_counts.get(source, 0)) + 1

    if state.get("last_discovery_source") == source:
        state["same_discovery_count"] = int(state.get("same_discovery_count", 0)) + 1
    else:
        state["last_discovery_source"] = source
        state["same_discovery_count"] = 1
