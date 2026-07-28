from __future__ import annotations

import logging
from typing import Any

from llms.deepseek import deepseek_model
from shared_schemas.entity import ExtractedEntity, ResolvedEntity

logger = logging.getLogger(__name__)


ENTITY_RESOLVER_PROMPT = """你是 AI Intelligence Agent 的实体标准化模块。

你的职责只回答：用户说的是谁。

你只负责标准化实体，不负责发现任何数据源。

禁止输出：
- GitHub owner/repo
- HuggingFace model id
- Reddit/X/YouTube/Blog URL
- sources
- identifier

输出 ResolvedEntity JSON：
{
  "name": "标准化名称",
  "entity_type": "project | technology | company | model | product | framework | unknown",
  "aliases": ["别名1", "别名2"],
  "official_name": "可选官方名称"
}

示例：

输入：LangGraph
输出：
{
  "name": "LangGraph",
  "entity_type": "project",
  "aliases": ["langgraph"],
  "official_name": "LangGraph"
}

输入：AI Agent
输出：
{
  "name": "AI Agent",
  "entity_type": "technology",
  "aliases": ["ai agent", "agentic ai"],
  "official_name": null
}

输入：OpenAI
输出：
{
  "name": "OpenAI",
  "entity_type": "company",
  "aliases": ["openai"],
  "official_name": "OpenAI"
}
"""


class EntityResolver:
    """仅标准化实体，不做数据源发现。"""

    def __init__(self):
        self.llm = deepseek_model.with_structured_output(ResolvedEntity)

    def resolve(self, entity: ExtractedEntity | dict[str, Any] | str) -> ResolvedEntity:
        name = self._extract_name(entity)
        if not name:
            return ResolvedEntity(name="", entity_type="unknown", aliases=[])

        try:
            result = self.llm.invoke(
                f"""{ENTITY_RESOLVER_PROMPT}

输入：{name}
"""
            )
            if isinstance(result, ResolvedEntity):
                return self._ensure_alias(result)
            if isinstance(result, dict):
                return self._ensure_alias(ResolvedEntity(**result))
        except Exception as exc:
            logger.warning("EntityResolver fallback: %s", exc)

        return self._rule_based_resolve(name)

    @staticmethod
    def _extract_name(entity: ExtractedEntity | dict[str, Any] | str) -> str:
        if isinstance(entity, str):
            return entity.strip()
        if isinstance(entity, ExtractedEntity):
            return entity.name.strip()
        return str(entity.get("name", "")).strip()

    @staticmethod
    def _ensure_alias(entity: ResolvedEntity) -> ResolvedEntity:
        if not entity.aliases and entity.name:
            entity.aliases = [entity.name.lower()]
        return entity

    @staticmethod
    def _rule_based_resolve(name: str) -> ResolvedEntity:
        normalized = name.strip()
        lowered = normalized.lower()

        known: dict[str, tuple[str, str, list[str], str | None]] = {
            "langgraph": ("LangGraph", "project", ["langgraph"], "LangGraph"),
            "langchain": ("LangChain", "project", ["langchain"], "LangChain"),
            "crewai": ("CrewAI", "project", ["crewai"], "CrewAI"),
            "autogen": ("AutoGen", "project", ["autogen", "microsoft autogen"], "AutoGen"),
            "dify": ("Dify", "project", ["dify"], "Dify"),
            "mastra": ("Mastra", "project", ["mastra"], "Mastra"),
            "openhands": ("OpenHands", "project", ["openhands"], "OpenHands"),
            "qwen": ("Qwen", "model", ["qwen"], "Qwen"),
            "deepseek": ("DeepSeek", "model", ["deepseek"], "DeepSeek"),
            "openai": ("OpenAI", "company", ["openai"], "OpenAI"),
            "anthropic": ("Anthropic", "company", ["anthropic"], "Anthropic"),
            "ai agent": ("AI Agent", "technology", ["ai agent", "agentic ai"], None),
            "ai agent framework": (
                "AI Agent Framework",
                "technology",
                ["ai agent framework", "agent framework"],
                None,
            ),
        }

        for key, value in known.items():
            if key in lowered:
                entity_name, entity_type, aliases, official_name = value
                return ResolvedEntity(
                    name=entity_name,
                    entity_type=entity_type,
                    aliases=aliases,
                    official_name=official_name,
                )

        entity_type = "technology" if any(
            kw in lowered for kw in ["ai", "agent", "framework", "memory", "模型", "技术"]
        ) else "unknown"

        return ResolvedEntity(
            name=normalized,
            entity_type=entity_type,
            aliases=[lowered],
            official_name=normalized,
        )
