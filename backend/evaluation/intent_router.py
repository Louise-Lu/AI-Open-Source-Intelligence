"""LLM-based Intent Router for evaluation Layer 1: 意图识别."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from llms.deepseek import deepseek_model
# from llms.qwen import qwen_model

VALID_INTENTS = [
    "project_overview",
    "repository",
    "readme",
    "release",
    "issue",
    "pr",
    "project_health",
    "roadmap",
    "recommendation",
    "comparison",
]

IntentLabel = Literal[
    "project_overview",
    "repository",
    "readme",
    "release",
    "issue",
    "pr",
    "project_health",
    "roadmap",
    "recommendation",
    "comparison",
]

INTENT_SET = set(VALID_INTENTS)

ROUTER_PROMPT = """你是一个 GitHub 开源项目分析 Agent 的 Intent Router。

根据用户问题判断所属意图。

允许多个意图。

只能从以下列表选择：

project_overview
repository
readme
release
issue
pr
project_health
roadmap
recommendation
comparison

返回 JSON：

{{
 "intents":[
    "xxx",
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
        self._llm = deepseek_model.with_structured_output(IntentClassification)
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
