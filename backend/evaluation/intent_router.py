"""LLM-based Intent Router for evaluation Layer 1: 意图识别."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from llms.deepseek import deepseek_structured_model
# from llms.qwen import qwen_model

VALID_INTENTS = [
    "information_lookup",
    "evaluation",
    "comparison",
    "trend_analysis",
    "technology_research",
    "market_research",
    "decision_support",
    "greeting",
    "small_talk",
    "help",
]

IntentLabel = Literal[
    "information_lookup",
    "evaluation",
    "comparison",
    "trend_analysis",
    "technology_research",
    "market_research",
    "decision_support",
    "greeting",
    "small_talk",
    "help",
]

INTENT_SET = set(VALID_INTENTS)

ROUTER_PROMPT = """你是一个开源项目分析 Agent 的 Intent Router。

根据用户问题判断所属意图。

只能从以下列表选择：

information_lookup — 用户只是了解一个对象，例如 "LangGraph 是什么"
evaluation — 评价一个项目/技术，例如 "LangGraph 怎么样"、"LangChain 最近社区怎么看"
comparison — 两个或多个对象比较，例如 "Qwen 和 DeepSeek 对比"
trend_analysis — 趋势分析，例如 "AI Agent 最近有什么趋势"
technology_research — 技术研究，例如 "LangGraph 原理"、"X 架构怎么实现"
market_research — 市场机会/市场空间，例如 "AI Agent 创业方向有没有机会"
decision_support — 用户需要建议/推荐/选型，例如 "推荐一个 AI Agent Framework"
greeting — 问候，例如 "hello"、"你好"
small_talk — 闲聊，例如 "谢谢"、"bye"、"今天天气怎么样"
help — 使用帮助，例如 "你能做什么"、"怎么用"、"help"

返回 JSON：

{{
 "intents":[
    "xxx"
 ]
}}

要求：
- 不输出解释
- 只输出 JSON

用户问题：
{question}
"""


class IntentClassification(BaseModel):
    intents: list[IntentLabel] = Field(default_factory=list)


class IntentRouter:
    def __init__(self) -> None:
        self._llm = deepseek_structured_model.with_structured_output(IntentClassification)
        # self._llm = qwen_model.with_structured_output(IntentClassification)

    def classify(self, question: str) -> list[str]:
        result = self._llm.invoke(ROUTER_PROMPT.format(question=question))
        intents = list(result.intents or [])
        # Deduplicate while preserving order; keep only valid labels.
        seen: set[str] = set()
        filtered: list[str] = []
        for intent in intents:
            if intent in INTENT_SET and intent not in seen:
                seen.add(intent)
                filtered.append(intent)
        return filtered
