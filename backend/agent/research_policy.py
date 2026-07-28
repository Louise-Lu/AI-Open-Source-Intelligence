from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


# 这个文件只做一件事：
# 记录 Research Agent 当前研究到哪一步了，并给 LLM 一段简单的 policy_hint。


@dataclass
class ObjectivePolicy:
    # 推荐的数据源顺序，例如 ["community", "web", "github"]
    preferred_sources: list[str]
    # 同一个 Discovery 来源最多连续搜索几次
    max_same_discovery: int
    # 至少拿到几个不同来源的证据，才算基本够用
    min_evidence_sources: int
    # 达到证据要求后，是否允许停止继续搜索
    stop_when_satisfied: bool

    # 兼容旧代码里的 policy.get(...)
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    # 兼容旧代码里的 policy["preferred_sources"]
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


# 不同研究目标，对应不同的数据源优先级和证据要求。
OBJECTIVE_POLICY: dict[str, ObjectivePolicy] = {
    "information_lookup": ObjectivePolicy(["github", "web", "community"], 2, 1, True),
    "evaluation": ObjectivePolicy(["github", "community", "web"], 2, 2, True),
    "comparison": ObjectivePolicy(["github", "community", "web"], 2, 2, True),
    "trend_analysis": ObjectivePolicy(["community", "web", "github"], 2, 3, True),
    "technology_research": ObjectivePolicy(["github", "web", "youtube"], 2, 2, True),
    "market_research": ObjectivePolicy(["community", "web", "github"], 2, 3, True),
    "decision_support": ObjectivePolicy(["github", "community", "web"], 2, 3, True),
}


DEFAULT_POLICY = ObjectivePolicy(["web", "github"], 2, 2, True)


# Discovery Tool：负责“发现资源”。
DISCOVERY_TOOL_SOURCE: dict[str, str] = {
    "github_search": "github",
    "huggingface_search": "huggingface",
    "community_search": "community",
    "youtube_search": "youtube",
    "web_search": "web",
}


# Evidence / Capability Tool：负责“读取证据”。
CAPABILITY_TOOL_SOURCE: dict[str, str] = {
    "github_project_profile": "github",
    "github_project_health": "github",
    "github_release_summary": "github",
    "github_ecosystem": "github",
    "huggingface_model_profile": "huggingface",
    "community_reader": "community",
    "webpage_reader": "web",
    "youtube_transcript": "youtube",
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
    "youtube": ["youtube_transcript"],
}


# 当前研究状态。ContextVar 可以避免不同请求之间互相污染。
_policy_state: ContextVar[dict[str, Any] | None] = ContextVar(
    "research_policy_state",
    default=None,
)



# {
#     "objective": "trend_analysis",
#     "policy": ObjectivePolicy(
#         preferred_sources=["community", "web", "github"],
#         max_same_discovery=2,
#         min_evidence_sources=3,
#         stop_when_satisfied=True,
#     ),
#     "last_discovery_source": None,
#     "same_discovery_count": 0,
#     "discovery_counts": {},
#     "discovered_resources": {},
#     "evidence_sources": [],
# }
# 当前是趋势分析。
# 优先 Community，再 Web，最后 GitHub。
# 同一个来源最多连续搜索 2 次。
# 希望至少拿到 3 个来源的证据。
# 现在还没有搜索过，也没有证据。

def start_research_policy(objective: str) -> None:
    """开始一次研究时调用：初始化 runtime policy 状态。"""
    policy = deepcopy(OBJECTIVE_POLICY.get(objective, DEFAULT_POLICY))
    _policy_state.set(
        {
            "objective": objective,
            "policy": policy,
            "last_discovery_source": None,
            "same_discovery_count": 0,
            "discovery_counts": {},      # 例：{"github": 1}
            "discovered_resources": {},  # 例：{"github": ["owner/repo"]}
            "evidence_sources": [],      # 例：["github", "community"]
        }
    )


def clear_research_policy() -> None:
    """研究结束后清空状态。"""
    _policy_state.set(None)


def get_research_policy_state() -> dict[str, Any]:
    """调试用：查看当前 policy_state。"""
    return _policy_state.get() or {}


def get_current_policy() -> ObjectivePolicy:
    """获取当前 objective 对应的 policy。"""
    state = _policy_state.get()
    if not state:
        return DEFAULT_POLICY
    return state.get("policy", DEFAULT_POLICY)

# 生成 给 LLM 看的自然语言提示prompt -> polict hint 
def build_policy_hint() -> str:
    """生成给 LLM 看的自然语言提示。"""
    state = _policy_state.get() or {}
    policy: ObjectivePolicy = state.get("policy", DEFAULT_POLICY)
    objective = str(state.get("objective", "unknown"))
    discovery_counts: dict[str, int] = state.get("discovery_counts", {}) or {}
    evidence_sources: list[str] = state.get("evidence_sources", []) or []

    progress = [
        f"- {_label(source)}: {_progress_text(discovery_counts.get(source, 0), policy.max_same_discovery)}"
        for source in policy.preferred_sources
    ]
    evidence = _evidence_text(evidence_sources)
    guidance = _guidance_text(policy, discovery_counts, evidence_sources)

    return (
        "Current Research Policy\n\n"
        "Research Objective\n"
        f"- {objective}\n\n"
        "Current Strategy\n"
        f"- 推荐数据源顺序：{' -> '.join(_label(s) for s in policy.preferred_sources)}\n\n"
        "Current Progress\n"
        f"{chr(10).join(progress)}\n\n"
        "Evidence\n"
        f"{evidence}\n\n"
        "Guidance\n"
        f"{guidance}"
    )

# 检查两件事：
# 这个来源是否已经发现过资源，如果发现过，就不应该继续 search，而应该去读 evidence。
# 这个来源是否已经连续调用超过 max_same_discovery。
def before_tool_call(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any] | None:
    """Tool 调用前检查：是否应该阻止这次 Discovery。"""
    state = _policy_state.get()
    if not state or tool_name not in DISCOVERY_TOOL_SOURCE:
        return None

    source = DISCOVERY_TOOL_SOURCE[tool_name]
    policy: ObjectivePolicy = state["policy"]

    # 规则 1：同一个来源已经发现资源了，就不要继续 search，应该去读 evidence。
    discovered = state.get("discovered_resources", {}).get(source, [])
    if discovered:
        tools = CAPABILITY_TOOLS_BY_SOURCE.get(source, [])
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason="已经发现资源，下一步应该读取证据，而不是继续搜索同一来源。",
            suggestion=f"建议调用 Evidence Tool: {', '.join(tools)}。已发现资源: {discovered[:3]}",
            tool_input=tool_input,
        )

    # 规则 2：同一个 Discovery 来源连续调用太多次，就要求切换来源。
    if (
        state.get("last_discovery_source") == source
        and int(state.get("same_discovery_count", 0)) >= policy.max_same_discovery
    ):
        alternatives = [s for s in policy.preferred_sources if s != source]
        return _policy_block(
            tool_name=tool_name,
            source=source,
            reason=f"{_label(source)} 已连续探索 {policy.max_same_discovery} 次。",
            suggestion=f"建议切换到: {', '.join(_label(s) for s in alternatives)}。",
            tool_input=tool_input,
        )

    return None


def after_tool_call(tool_name: str, tool_output: Any) -> None:
    """Tool 调用后更新状态：Discovery 计数、已发现资源、已获得证据来源。"""
    state = _policy_state.get()
    if not state:
        return

    if tool_name in DISCOVERY_TOOL_SOURCE:
        _record_discovery(state, tool_name, tool_output)
        return

    if tool_name in CAPABILITY_TOOL_SOURCE:
        source = CAPABILITY_TOOL_SOURCE[tool_name]
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
        }
    )

    for item in trace:
        after_tool_call(str(item.get("tool", "")), item.get("output"))


def needs_trend_single_source_warning() -> bool:
    """趋势分析如果只有 GitHub 证据，需要提醒用户证据不足。"""
    state = _policy_state.get()
    if not state or state.get("objective") != "trend_analysis":
        return False
    return set(state.get("evidence_sources", [])) == {"github"}


def trend_single_source_warning() -> str:
    return "目前仅获得 GitHub 证据，社区观点不足。"


def source_for_tool(tool_name: str) -> str | None:
    """兼容外部调用：返回 tool 对应的数据源。"""
    return DISCOVERY_TOOL_SOURCE.get(tool_name) or CAPABILITY_TOOL_SOURCE.get(tool_name)

# 更新 state的三块地方
# 更新 last_discovery_source
# 更新 discovery_counts
# 更新 discovered_resources 
def _record_discovery(state: dict[str, Any], tool_name: str, tool_output: Any) -> None:
    """记录一次 Discovery Tool 调用。"""
    source = DISCOVERY_TOOL_SOURCE[tool_name]

    if state.get("last_discovery_source") == source:
        state["same_discovery_count"] = int(state.get("same_discovery_count", 0)) + 1
    else:
        state["last_discovery_source"] = source
        state["same_discovery_count"] = 1

    counts = state.setdefault("discovery_counts", {})
    counts[source] = int(counts.get(source, 0)) + 1

    resources = _extract_discovery_identifiers(tool_output)
    if resources:
        discovered = state.setdefault("discovered_resources", {})
        discovered.setdefault(source, [])
        for item in resources:
            if item not in discovered[source]:
                discovered[source].append(item)


def _extract_discovery_identifiers(tool_output: Any) -> list[str]:
    """从 DiscoveryResult 列表里取 identifier。"""
    if not isinstance(tool_output, list):
        return []

    identifiers: list[str] = []
    for item in tool_output:
        if isinstance(item, dict) and item.get("identifier"):
            identifiers.append(str(item["identifier"]))
    return identifiers


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


def _label(source: str) -> str:
    """把内部 source 名称转成给 LLM 看的名称。"""
    return {
        "github": "GitHub",
        "web": "Web",
        "community": "Community",
        "youtube": "YouTube",
        "huggingface": "HuggingFace",
    }.get(source, source)


def _progress_text(count: int, max_count: int) -> str:
    if count <= 0:
        return "未探索"
    if count >= max_count:
        return f"已探索（{count} 次，建议切换）"
    return f"已探索（{count} 次）"


def _evidence_text(evidence_sources: list[str]) -> str:
    if not evidence_sources:
        return "- 暂无已收集证据。"
    return "\n".join(f"- 已获得 {_label(source)} 证据。" for source in evidence_sources)


def _guidance_text(
    policy: ObjectivePolicy,
    discovery_counts: dict[str, int],
    evidence_sources: list[str],
) -> str:
    """生成简单指导，不追求复杂推理，只提醒下一步该做什么。"""
    evidence_count = len(set(evidence_sources))

    if policy.stop_when_satisfied and evidence_count >= policy.min_evidence_sources:
        return "- 已达到最低证据来源要求，可以停止搜索并生成结论。"

    for source in policy.preferred_sources:
        if discovery_counts.get(source, 0) >= policy.max_same_discovery:
            return f"- {_label(source)} 已探索较多，建议切换到其它来源交叉验证。"

    if not evidence_sources:
        return (
            f"- 从 {_label(policy.preferred_sources[0])} 开始。\n"
            "- Discovery 只用于发现资源；找到资源后，应立即使用 Evidence Tool。"
        )

    return (
        f"- 当前已有 {evidence_count} 个证据来源，目标是至少 {policy.min_evidence_sources} 个。\n"
        "- 继续探索下一个优先数据源，补充交叉验证。"
    )
