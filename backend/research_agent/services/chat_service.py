# ChatService — AI Intelligence Research Agent 入口
#
# 流程（含 Guard）：
#   User Query
#     → IntentRouter
#           ├── greeting/small_talk/help → Chat Response → END
#           └── information_lookup/evaluation/comparison/... → Entity → Context Builder → Runtime → Agent → Signals → Brief
#
# Fail Fast 原则：
# - 非研究意图 → 立即结束
# - 无实体 → Context Builder 返回 need_user_input，Agent 不启动
# - 无证据 → Analyzer 返回空，Composer 返回 insufficient_information

# 用户问题
#   -> IntentRouter 理解意图
#   -> EntityExtractor 抽实体
#   -> EntityResolver 标准化实体
#   -> ContextBuilder 生成 ResearchContext + ExecutionPlan
#   -> ResearchPolicy 初始化运行时策略
#   -> ToolGateway 统一拦截工具调用
#   -> ReAct Agent 在允许范围内搜索/读取/停止

from __future__ import annotations

import json
import time
from typing import Any

from agent.intelligence_agent import build_intelligence_agent_prompt, intelligence_agent
from agent.research_policy import (
    clear_research_policy,
    needs_trend_single_source_warning,
    start_research_policy,
    sync_research_policy_from_trace,
)
from agent.trace import clear_trace, get_discovered_resources, get_evidence_store, get_trace, populate_trace_from_agent_result

from research_agent.intent import ResearchIntentRouter
from research_agent.entity_extractor import EntityExtractor
from research_agent.entity_resolver import EntityResolver

from research_agent.context_builder import ResearchContextBuilder

from research_agent.signal_extractor import ResearchAgentAnalyzer
from research_agent.composer import ResearchBriefComposer


from research_agent.schemas.research import (
    ExtractedSignals,
    ResearchIntent,
    ResearchObjective,
)

from shared_schemas.entity import ResolvedEntity


# 非研究类意图集合（不走 Research Pipeline）
_CHAT_ONLY_OBJECTIVES: set[str] = {
    ResearchObjective.greeting.value,
    ResearchObjective.small_talk.value,
    ResearchObjective.help.value,
}


def _build_chat_response(intent: ResearchIntent) -> dict:
    """为非研究类意图生成直接回复。"""
    obj = intent.objective
    if obj == ResearchObjective.greeting.value:
        answer = (
            "你好！我是 AI Intelligence Research Agent，"
            "可以帮你研究开源项目、技术趋势和竞品分析。"
            "有什么想研究的吗？"
        )
    elif obj == ResearchObjective.small_talk.value:
        answer = (
            "你好！我专注于开源情报研究，"
            "可以帮你分析项目、对比技术、追踪趋势。"
            "有什么研究需求吗？"
        )
    elif obj == ResearchObjective.help.value:
        answer = (
            "我可以帮你做以下研究：\n"
            "- 项目评估：分析 GitHub 项目的活跃度、社区健康度、风险\n"
            "- 竞品对比：比较多个框架/工具的优劣\n"
            "- 趋势分析：追踪技术方向的最新动态\n"
            "- 技术研究：深入了解某项技术的原理和架构\n\n"
            "请告诉我你想研究什么项目或技术？"
        )
    else:
        answer = "你好！有什么可以帮你的吗？"

    ui_trace = {
        "intent": intent.model_dump(),
        "discovered_sources": {},
        "steps": [],
        "react_steps": [],
    }
    return {"answer": answer, "trace": ui_trace, "error": None}


def _recursion_limit_for_context(research_context: Any, minimum: int = 12) -> int:
    """根据 execution_plan 工具预算推导 LangGraph recursion_limit。"""
    execution_plan = getattr(research_context, "execution_plan", None)
    max_tool_calls = int(getattr(execution_plan, "max_tool_calls", 6) or 6)
    # 每个工具调用约 2 个图步骤，额外预留 system/user/final/reflection 空间。
    return max(minimum, max_tool_calls * 2 + 6)


class ChatService:
    """AI Intelligence Research Agent 主服务。

    混合架构 + Fail Fast Guard:
    - Router / Entity 层保留确定性理解与解析
    - Research Context Builder 输出 ResearchContext，而不是步骤计划
    - Intelligence Agent 用 ReAct 循环自主选择工具
    - Analyzer / Composer 保留结构化输出层

    - 非研究意图不走 Research Pipeline
    - 无实体不启动 Agent
    - 无证据不生成信号和简报
    """

    def __init__(self):
        self.router = ResearchIntentRouter()
        self.entity_extractor = EntityExtractor()
        self.entity_resolver = EntityResolver()
        self.context_builder = ResearchContextBuilder()
        self.agent = intelligence_agent
        # LangGraph recursion_limit 不是业务工具预算。
        # 一个 tool call 通常会消耗 AIMessage + ToolMessage 两个图步骤，还需要最终回答步骤。
        # 真实工具预算由 ResearchPolicy / execution_plan.max_tool_calls 控制。
        self.min_recursion_limit = 12
        # 快速模式：跳过 Analyzer 的多次结构化 LLM，只用 evidence 交给 Composer 生成答案。
        # 如果后续需要更完整的结构化信号，把这里改成 True。
        self.use_structured_analyzer = False
        # 快速模式：跳过 Composer LLM，直接基于 evidence 生成简报。
        # 如果需要更自然的长文分析，把这里改成 True。
        self.use_llm_composer = False
        self.analyzer = ResearchAgentAnalyzer()
        self.composer = ResearchBriefComposer()


    def chat(self, message: str) -> dict:
        """主入口: 接收用户消息，返回研究结果。"""
        t0 = time.perf_counter()
        print(f"[聊天服务] 开始处理用户消息: {message[:200]!r}")

        clear_trace()

        intent = self.router.route(message)
        print(
            "[聊天服务] 1. 意图识别完成: "
            f"objective={intent.objective}, "
            f"entities={intent.entities},"
            f"depth={intent.depth}"
        )

        if intent.objective in _CHAT_ONLY_OBJECTIVES:
            print(f"[聊天服务] 非研究类意图，直接返回: objective={intent.objective}")
            return _build_chat_response(intent)
        
        resolved_entities = self._extract_and_resolve(message, intent)
        print(
            "[聊天服务] 2. 实体解析完成: "
            f"数量={len(resolved_entities)}, "
            f"名称={[e.name for e in resolved_entities]}"
        )

        research_context = self.context_builder.build(intent, resolved_entities)
        if research_context is None:
            print("[聊天服务] 未识别到研究对象，返回 need_user_input")
            return self._build_need_user_response(intent=intent)

        print(
            "[聊天服务] 3. 上下文构建完成: "
            f"objective={research_context.objective}, "
            f"user_goal={research_context.user_goal[:120]}, "
            f"depth={research_context.depth}, "
            f"execution_plan={research_context.execution_plan}"
        )
    
        agent_error = None
        agent_result = None
        t_agent = time.perf_counter()
        try:
            # 初始化 policy_state
            start_research_policy(research_context)
            
            # 构建 prompt + policy_hint
            agent_prompt = build_intelligence_agent_prompt(research_context, resolved_entities)
            recursion_limit = _recursion_limit_for_context(research_context, self.min_recursion_limit)
            print(f"[聊天服务] Agent recursion_limit={recursion_limit}")
            agent_result = self.agent.invoke(
                {
                    "messages": [
                        ("system", agent_prompt),
                        ("user", message),
                    ]
                },
                config={"recursion_limit": recursion_limit},
            )
        except Exception as exc:  # noqa: BLE001
            agent_error = f"{type(exc).__name__}: {exc}"
            agent_result = {"error": agent_error, "messages": []}
            print(f"[聊天服务] Agent 调用失败: {agent_error}")

        print(
            "[聊天服务] 4. Agent 调用结束: "
            f"耗时={time.perf_counter() - t_agent:.2f}s, "
            f"错误={agent_error}, "
            f"消息数量={len(agent_result.get('messages', [])) if isinstance(agent_result, dict) else 0}"
        )

        populate_trace_from_agent_result(agent_result)
        sync_research_policy_from_trace(get_trace())


        evidences = get_evidence_store()

        source_names = []
        for evidence in evidences:
            if evidence.github:
                source_names.append("github")
            if evidence.web:
                source_names.append("web")
            if evidence.reddit:
                source_names.append("community")
            if evidence.huggingface:
                source_names.append("huggingface")

        print(
            "[聊天服务] 5. 证据收集完成: "
            f"证据对象数量={len(evidences)}, "
            f"证据来源={source_names}, "
            f"来源数量={len(set(source_names))}, "
            f"trace数量={len(get_trace())}"
        )

        if not evidences:
            print("[聊天服务] 未获取到证据，返回证据不足响应")
            clear_research_policy()
            return self._build_insufficient_evidence_response(
                intent=intent,
                agent_result=agent_result,
                agent_error=agent_error,
            )

        t_analyzer = time.perf_counter()
        if self.use_structured_analyzer:
            signals = self.analyzer.analyze(evidences, research_context)
            analyzer_mode = "structured"
        else:
            signals = ExtractedSignals()
            analyzer_mode = "skipped"
        print(
            "[聊天服务] 6. 信号提取完成: "
            f"模式={analyzer_mode}, "
            f"耗时={time.perf_counter() - t_analyzer:.2f}s, "
            f"是否有信号={signals.has_any_signal}, "
            f"技术={signals.technology is not None}, "
            f"社区={signals.community is not None}, "
            f"生态={signals.ecosystem is not None}, "
            f"风险={signals.risks is not None}"
        )

        t_composer = time.perf_counter()
        if self.use_llm_composer:
            brief = self.composer.compose(message, evidences, signals)
            composer_mode = "llm"
        else:
            brief = self.composer.compose_fast(message, evidences, signals)
            composer_mode = "fast"
        print(
            "[聊天服务] Composer 生成完成: "
            f"模式={composer_mode}, "
            f"耗时={time.perf_counter() - t_composer:.2f}s"
        )
        if needs_trend_single_source_warning():
            warning = "目前仅获得 GitHub 证据，社区观点不足。"
            if warning not in brief.key_findings:
                brief.key_findings.append(warning)
            if warning not in brief.analysis:
                brief.analysis = f"{brief.analysis}\n\n{warning}".strip()

        print(
            "[聊天服务] 7. 研究简报生成完成: "
            f"summary长度={len(brief.summary)}, "
            f"关键发现数量={len(brief.key_findings)}, "
            f"来源数量={len(brief.sources)}"
        )

        response = self._build_response(
            intent=intent,
            agent_result=agent_result,
            agent_error=agent_error,
            brief=brief,
        )
        if not self.use_llm_composer:
            agent_answer = _extract_final_agent_answer(agent_result)
            if agent_answer:
                response["answer"] = agent_answer
                print("[聊天服务] 使用 Agent 最终回答，跳过 fast composer 文本作为最终输出")
        print(
            "[聊天服务] 处理完成: "
            f"总耗时={time.perf_counter() - t0:.2f}s, "
            f"回答长度={len(response.get('answer', ''))}, "
            f"步骤数量={len(response.get('trace', {}).get('steps', []))}"
        )
        clear_research_policy()
        return response

    # ── Entity Resolution ──────────────────────────────────────
    def _extract_and_resolve(
        self,
        message: str,
        intent: ResearchIntent,
    ) -> list[ResolvedEntity]:
        # 1. 先直接用意图中的实体
        all_entity_names = set(intent.entities) if intent.entities else set()

        # 2. 只有在意图中没有实体时，才调实体提取
        if not all_entity_names:
            entity_result = self.entity_extractor.extract(message)
            entity_dict = (
                entity_result
                if isinstance(entity_result, dict)
                else entity_result.model_dump()
            )
            for entity in entity_dict.get("entities", []):
                name = entity.get("name", "")
                if name:
                    all_entity_names.add(name)

        # 3. 解析实体
        resolved = []
        for name in all_entity_names:
            if name:
                result = self.entity_resolver.resolve(name)
                if result and result.name:
                    resolved.append(result)
                else:
                    print(f"[聊天服务] 实体解析为空: name={name}")
        return resolved


    # ── Response Builders ───────────────────────────────────────
    @staticmethod
    def _build_need_user_response(
        intent: ResearchIntent,
    ) -> dict:
        """当无法识别研究对象时，向用户请求补充信息。"""
        answer = (
            "未识别到需要研究的对象，请提供项目名称或 GitHub Repository。\n\n"
            "例如：\n"
            "- LangGraph\n"
            "- OpenHands\n"
            "- Mastra\n"
            "- owner/repo"
        )
        ui_trace = {
            "intent": intent.model_dump(),
            "discovered_sources": {},
            "steps": [],
            "react_steps": [],
        }
        return {"answer": answer, "trace": ui_trace, "error": None}

    @staticmethod
    def _build_insufficient_evidence_response(
        intent: ResearchIntent,
        agent_result: Any,
        agent_error: str | None,
    ) -> dict:
        """当 Agent 没有获取到任何证据时，直接返回失败信息。"""
        answer = (
            "没有获取到任何证据，因此无法继续研究。\n\n"
            "可能原因：\n"
            "- 目标仓库不存在或无法访问\n"
            "- 网络/API 限制\n"
            "- 研究对象没有公开数据\n\n"
            "请尝试提供其他项目名称或 GitHub 仓库地址。"
        )
        ui_trace = {
            "intent": intent.model_dump(),
            "discovered_sources": _sanitize_value(get_discovered_resources()),
            "steps": _extract_react_steps(agent_result),
        }
        ui_trace["react_steps"] = ui_trace["steps"]
        return {"answer": answer, "trace": ui_trace, "error": agent_error}

    @staticmethod
    def _build_response(
        intent: ResearchIntent,
        agent_result: Any,
        agent_error: str | None,
        brief,
    ) -> dict:
        """构建最终响应。"""
        answer = brief.summary
        if brief.key_findings:
            answer += "\n\n**关键发现:**\n" + "\n".join(
                f"- {finding}" for finding in brief.key_findings
            )
        if brief.analysis:
            answer += f"\n\n**分析:**\n{brief.analysis}"
        if brief.recommendations:
            answer += "\n\n**建议:**\n" + "\n".join(
                f"- {recommendation}" for recommendation in brief.recommendations
            )
        if brief.sources:
            answer += "\n\n**信息来源:**\n" + "\n".join(
                f"- {source}" for source in brief.sources
            )

        ui_trace = {
            "intent": intent.model_dump(),
            "discovered_sources": _sanitize_value(get_discovered_resources()),
            "steps": _extract_react_steps(agent_result),
        }
        ui_trace["react_steps"] = ui_trace["steps"]

        if agent_error:
            answer = (
                "研究 Agent 调用模型失败，当前没有完成自主工具探索。\n\n"
                f"错误信息：`{agent_error}`"
            )

        # 响应体大小控制：截断过长的 answer
        MAX_ANSWER_LENGTH = 5000
        if len(answer) > MAX_ANSWER_LENGTH:
            answer = answer[:MAX_ANSWER_LENGTH] + "\n\n...(报告过长已截断)"

        return {"answer": answer, "trace": ui_trace, "error": agent_error}


# 单个工具输出最大字符数（防止 README 等大文本撑爆响应体）
_MAX_TOOL_OUTPUT_CHARS = 2000
_MAX_THOUGHT_CHARS = 200
_MAX_OBSERVATION_CHARS = 300


def _truncate_text(value: Any, max_chars: int) -> str:
    """将任意值转换为字符串并截断，供前端 UI trace 展示。"""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(value)
    if len(text) <= max_chars:
        return text
    suffix = "...(truncated)"
    return text[: max_chars - len(suffix)] + suffix


def _parse_tool_content(content: Any) -> Any:
    """尽量把 ToolMessage.content 解析为 JSON，失败时保留原字符串。"""
    if not isinstance(content, str):
        return content
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return content


def _format_observation_for_ui(content: Any) -> str:
    """格式化前端 Observation。

    Tool 返回给 LLM 的 observation 现在包含：
    - result: 工具原始结果
    - policy_hint: 最新 Research Policy

    前端只展示 observation 字段，所以这里提前整理成更容易读的文本。
    """
    parsed = _parse_tool_content(content)
    if isinstance(parsed, dict) and "result" in parsed and "policy_hint" in parsed:
        result_text = _truncate_text(parsed.get("result"), _MAX_OBSERVATION_CHARS)
        policy_text = _truncate_text(parsed.get("policy_hint"), 800)
        return (
            "Tool Result:\n"
            f"{result_text}\n\n"
            "Latest Policy Hint:\n"
            f"{policy_text}"
        )

    return _truncate_text(parsed, _MAX_OBSERVATION_CHARS)


def _get_message_type(message: Any) -> str:
    return str(getattr(message, "type", "") or "")


def _extract_final_agent_answer(agent_result: Any) -> str:
    """提取 ReAct Agent 已生成的最终回答，避免 fast composer 覆盖自然语言结论。"""
    if not isinstance(agent_result, dict):
        return ""
    messages = agent_result.get("messages", []) or []
    for msg in reversed(messages):
        if _get_message_type(msg) != "ai":
            continue
        if getattr(msg, "tool_calls", []) or []:
            continue
        content = str(getattr(msg, "content", "") or "").strip()
        if len(content) >= 80:
            return content
    return ""


def _extract_react_steps(agent_result: dict | None) -> list[dict[str, Any]]:
    """从 LangGraph agent_result 中提取前端可渲染的 ReAct 步骤。"""
    if not isinstance(agent_result, dict):
        return []

    messages = agent_result.get("messages", [])
    if not messages:
        return []

    steps: list[dict[str, Any]] = []
    pending_tc: dict[str, tuple[str, dict[str, Any]]] = {}
    step_by_tool_call_id: dict[str, dict[str, Any]] = {}

    for msg_index, msg in enumerate(messages):
        msg_type = _get_message_type(msg)
        is_last_message = msg_index == len(messages) - 1

        if msg_type == "ai":
            tool_calls = getattr(msg, "tool_calls", []) or []
            content = getattr(msg, "content", "") or ""

            if tool_calls:
                for call_index, tool_call in enumerate(tool_calls):
                    tool_call_id = tool_call.get("id", "")
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {}) or {}
                    pending_tc[tool_call_id] = (tool_name, tool_args)

                    step = {
                        "index": len(steps) + 1,
                        "thought": _truncate_text(
                            content if call_index == 0 else "同一轮工具调用",
                            _MAX_THOUGHT_CHARS,
                        ),
                        "action": {
                            "tool": tool_name,
                            "input": _sanitize_value(tool_args),
                        },
                        "observation": "",
                    }
                    steps.append(step)
                    if tool_call_id:
                        step_by_tool_call_id[tool_call_id] = step
                continue

            if is_last_message:
                steps.append(
                    {
                        "index": len(steps) + 1,
                        "thought": _truncate_text(content, _MAX_THOUGHT_CHARS),
                        "action": None,
                        "observation": "（生成最终回答）",
                    }
                )

        elif msg_type == "tool":
            tool_call_id = getattr(msg, "tool_call_id", "") or ""
            tool_name = getattr(msg, "name", "") or ""
            content = getattr(msg, "content", "")
            observation = _format_observation_for_ui(content)

            step = step_by_tool_call_id.get(tool_call_id)
            if step is None:
                # 兼容缺少 AIMessage tool_call 记录的异常情况。
                pending_name, pending_args = pending_tc.get(
                    tool_call_id,
                    (tool_name, {}),
                )
                step = {
                    "index": len(steps) + 1,
                    "thought": "",
                    "action": {
                        "tool": pending_name or tool_name,
                        "input": _sanitize_value(pending_args),
                    },
                    "observation": "",
                }
                steps.append(step)
                if tool_call_id:
                    step_by_tool_call_id[tool_call_id] = step

            step["observation"] = observation

    return steps


def _sanitize_value(value: Any, max_str_len: int = _MAX_TOOL_OUTPUT_CHARS) -> Any:
    """递归地将任意值转换为 JSON 安全的基本类型，并截断过长的字符串。"""
    if value is None:
        return None
    if isinstance(value, str):
        return value[:max_str_len] + "...(truncated)" if len(value) > max_str_len else value
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item, max_str_len) for item in value[:50]]
    if isinstance(value, dict):
        return {str(k): _sanitize_value(v, max_str_len) for k, v in list(value.items())[:50]}
    # Pydantic models
    if hasattr(value, "model_dump"):
        return _sanitize_value(value.model_dump(), max_str_len)
    if hasattr(value, "dict"):
        return _sanitize_value(value.dict(), max_str_len)
    # Fallback: stringify
    return str(value)[:max_str_len]
