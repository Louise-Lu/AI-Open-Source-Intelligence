from __future__ import annotations

import json
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from evidence import EvidenceBuilder, IntelligenceEvidence


tool_trace: ContextVar[list[dict[str, Any]]] = ContextVar(
    "tool_trace",
    default=[],
)


def add_trace(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: Any,
) -> None:
    trace = list(tool_trace.get())
    trace.append(
        {
            "step_index": len(trace),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "input": tool_input,
            "output": tool_output,
        }
    )
    tool_trace.set(trace)


def get_trace() -> list[dict[str, Any]]:
    return list(tool_trace.get())


def clear_trace() -> None:
    tool_trace.set([])


def unwrap_tool_output(output: Any) -> Any:
    """兼容带 policy_hint 的 Tool Observation。

    Tool 返回给 LLM 时会包装成：
    {"result": 原始工具结果, "policy_hint": 最新策略提示}

    但 trace/evidence 解析只关心原始工具结果，所以这里统一拆出来。
    """
    if isinstance(output, dict) and "result" in output and "policy_hint" in output:
        return output.get("result")
    return output


def get_discovered_resources() -> dict[str, list[Any]]:
    """从 trace 中提取 Agent 自主发现的数据源资源。
      "例如:
        discovered_sources": {
            "github": [
                "crewAIInc/crewAI",
                "adongwanai/AgentGuide"
            ]
  """
    discovered: dict[str, list[Any]] = {
        "github": [],
        "huggingface": [],
        "community": [],
        "web": [],
        "youtube": [],
    }
    for item in get_trace():
        tool_name = item.get("tool")
        output = unwrap_tool_output(item.get("output"))
        if isinstance(output, dict) and output.get("source") == "research_policy":
            continue

        if tool_name == "github_search":
            for repo in _as_list(output):
                identifier = repo.get("identifier") if isinstance(repo, dict) else repo
                if identifier:
                    discovered["github"].append(identifier)
        elif tool_name == "huggingface_search":
            for model in _as_list(output):
                model_id = model.get("identifier") if isinstance(model, dict) else None
                if model_id:
                    discovered["huggingface"].append(model_id)
        elif tool_name == "community_search":
            for item in _as_list(output):
                identifier = item.get("identifier") if isinstance(item, dict) else item
                if identifier:
                    discovered["community"].append(identifier)
        elif tool_name == "youtube_search":
            for item in _as_list(output):
                identifier = item.get("identifier") if isinstance(item, dict) else item
                if identifier:
                    discovered["youtube"].append(identifier)
        elif tool_name == "web_search":
            for item in _as_list(output):
                identifier = item.get("identifier") if isinstance(item, dict) else item
                if identifier:
                    discovered["web"].append(identifier)

    return {
        key: list(dict.fromkeys(value))
        for key, value in discovered.items()
        if value
    }


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def get_evidence_store() -> list[IntelligenceEvidence]:
    """把工具 trace 聚合为 Analyzer/Composer 可消费的结构化证据。"""
    trace = get_trace()

    if not trace:
        return []

    github_raw: dict[str, Any] = {}
    huggingface_raw: dict[str, Any] | None = None
    reddit_raw: dict[str, Any] | None = None

    for item in trace:
        tool_name = item.get("tool")
        output = unwrap_tool_output(item.get("output"))

        if tool_name in {
            "github_search",
            "huggingface_search",
            "community_search",
            "youtube_search",
            "web_search",
        }:
            continue

        if isinstance(output, dict) and output.get("source") == "github":
            evidence = output.get("evidence")
            if isinstance(evidence, dict):
                github_raw.update(evidence)
            continue

        if isinstance(output, dict) and output.get("source") == "huggingface":
            evidence = output.get("evidence")
            if isinstance(evidence, dict):
                model = evidence.get("model")
                if isinstance(model, dict):
                    huggingface_raw = model
            continue

        if isinstance(output, dict) and output.get("source") == "community":
            evidence = output.get("evidence")
            if isinstance(evidence, dict):
                reddit_raw = {
                    "posts": [str(evidence.get("content") or evidence.get("identifier") or "")],
                    "sentiment": None,
                    "mentions": 1,
                }
            continue

        if tool_name == "get_repository_info":
            github_raw["repository"] = output
        elif tool_name == "readme":
            github_raw["readme"] = output
        elif tool_name == "releases":
            github_raw["releases"] = output
        elif tool_name == "issues":
            github_raw["issues"] = output
        elif tool_name == "pull_requests":
            github_raw["pull_requests"] = output
        elif tool_name == "get_commit_activity":
            github_raw["commit_activity"] = output
        elif tool_name == "get_planning_signals":
            github_raw["planning"] = output
        elif tool_name == "get_discussion_signals":
            github_raw["discussions"] = output
    has_evidence = bool(github_raw or huggingface_raw or reddit_raw)
    if not has_evidence:
        return []

    builder = EvidenceBuilder()
    evidence = builder.build(
        repository=github_raw.get("repository"),
        readme=github_raw.get("readme"),
        releases=github_raw.get("releases"),
        issues=github_raw.get("issues"),
        pull_requests=github_raw.get("pull_requests"),
        commit_activity=github_raw.get("commit_activity"),
        planning=github_raw.get("planning"),
        discussions=github_raw.get("discussions"),
        ecosystem=github_raw.get("ecosystem"),
        huggingface=huggingface_raw,
        reddit=reddit_raw,
    )
    return [evidence]


def populate_trace_from_agent_result(agent_result: Any) -> None:
    """从 LangGraph agent invoke 结果中提取 ToolMessage，回填到 trace。

    LangGraph 的 create_react_agent 在异步/线程上下文中执行工具，
    ContextVar 的写入不会传播回主上下文。此函数在 invoke 返回后，
    从 messages 中提取工具调用记录并回填 trace。
    """
    if not isinstance(agent_result, dict):
        return

    messages = agent_result.get("messages", [])
    if not messages:
        return

    existing_trace = get_trace()
    # 如果 trace 已经有记录（例如同步执行场景），不需要回填
    if existing_trace:
        return

    # 遍历 messages，提取 ToolMessage 并回填
    # 同时收集对应的 AIMessage 中的 tool_call input
    pending_tool_calls: dict[str, dict[str, Any]] = {}  # tool_call_id -> args

    for msg in messages:
        msg_type = getattr(msg, "type", None)

        # 从 AIMessage 中收集 tool_call 的参数
        if msg_type == "ai":
            tool_calls = getattr(msg, "tool_calls", []) or []
            for tc in tool_calls:
                tc_id = tc.get("id", "")
                tc_name = tc.get("name", "")
                tc_args = tc.get("args", {})
                if tc_id and tc_name:
                    pending_tool_calls[tc_id] = {
                        "name": tc_name,
                        "args": tc_args,
                    }

        # 从 ToolMessage 中提取工具名和输出
        elif msg_type == "tool":
            tool_name = getattr(msg, "name", None) or ""
            tool_call_id = getattr(msg, "tool_call_id", "") or ""
            content = getattr(msg, "content", "")

            # 尝试解析 content（可能是 JSON 字符串或纯文本）
            parsed_output: Any = content
            if isinstance(content, str):
                try:
                    parsed_output = json.loads(content)
                except (json.JSONDecodeError, ValueError):
                    parsed_output = content

            # 获取对应的 tool input
            tool_input = pending_tool_calls.get(tool_call_id, {}).get("args", {})

            add_trace(tool_name, tool_input, parsed_output)
