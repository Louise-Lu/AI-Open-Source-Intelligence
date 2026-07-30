from __future__ import annotations

import logging
from typing import Any

from llms.deepseek import deepseek_structured_model
from research_agent.schemas.entity import ExtractedEntity, ResolvedEntity

logger = logging.getLogger(__name__)


ENTITY_RESOLVER_PROMPT = """你是 AI Intelligence Agent 的实体标准化模块。

你的职责回答三个问题：
1. 用户说的是谁（标准化名称）
2. 这个实体的信息存在于哪些平台（entity_scope）
3. 这个实体是中国项目还是海外项目（entity_origin）

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
  "entity_scope": ["github", "web"],
  "entity_origin": "chinese | international | unknown",
  "aliases": ["别名1", "别名2"],
  "official_name": "可选官方名称"
}

entity_scope 判断规则：
- github: 有开源代码仓库的项目（如 LangGraph、Dify、CrewAI）
- huggingface: 有 HuggingFace 模型的项目（如 Qwen、DeepSeek、Llama）
- web: 有官方网站/文档/博客（几乎所有实体都有）

示例：
- 开源框架/项目 → ["github", "web"]
- AI 模型 → ["github", "huggingface", "web"]
- 公司/组织 → ["web"]
- 技术概念/趋势 → ["web"]

entity_origin 判断规则：
- chinese: 中国公司/团队开发的项目（如 Dify、Qwen、DeepSeek、通义千问）
- international: 海外公司/团队开发的项目（如 LangGraph、CrewAI、OpenAI GPT）
- unknown: 无法确定归属（如技术概念 "AI Agent"）

示例：

输入：LangGraph
输出：
{
  "name": "LangGraph",
  "entity_scope": ["github", "web"],
  "entity_origin": "international",
  "aliases": ["langgraph"],
  "official_name": "LangGraph"
}

输入：Qwen
输出：
{
  "name": "Qwen",
  "entity_scope": ["github", "huggingface", "web"],
  "entity_origin": "chinese",
  "aliases": ["qwen", "通义千问"],
  "official_name": "Qwen"
}

输入：OpenAI
输出：
{
  "name": "OpenAI",
  "entity_scope": ["web"],
  "entity_origin": "international",
  "aliases": ["openai"],
  "official_name": "OpenAI"
}

输入：AI Agent
输出：
{
  "name": "AI Agent",
  "entity_scope": ["web"],
  "entity_origin": "unknown",
  "aliases": ["ai agent", "agentic ai"],
  "official_name": null
}
"""


class EntityResolver:
    """仅标准化实体，不做数据源发现。"""

    def __init__(self):
        self.llm = deepseek_structured_model.with_structured_output(ResolvedEntity)

    def resolve(self, entity: ExtractedEntity | dict[str, Any] | str) -> ResolvedEntity:
        name = self._extract_name(entity)
        if not name:
            return ResolvedEntity(name="", entity_scope=["web"], aliases=[])

        try:
            result = self.llm.invoke(
                f"""{ENTITY_RESOLVER_PROMPT}

输入：{name}
"""
            )
            if isinstance(result, ResolvedEntity):
                resolved = self._ensure_alias(result)
            elif isinstance(result, dict):
                resolved = self._ensure_alias(ResolvedEntity(**result))
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
            print(
                f"[实体解析] LLM 成功: {name} → "
                f"name={resolved.name}, scope={resolved.entity_scope}, "
                f"origin={resolved.entity_origin}"
            )
            return resolved
        except Exception as exc:
            print(f"[实体解析] LLM 失败，走规则兜底: {name}, 原因: {exc}")
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

        # key: (name, entity_scope, entity_origin, aliases, official_name)
        known: dict[str, tuple[str, list[str], str, list[str], str | None]] = {
            "langgraph": ("LangGraph", ["github", "web"], "international", ["langgraph"], "LangGraph"),
            "langchain": ("LangChain", ["github", "web"], "international", ["langchain"], "LangChain"),
            "crewai": ("CrewAI", ["github", "web"], "international", ["crewai"], "CrewAI"),
            "autogen": ("AutoGen", ["github", "web"], "international", ["autogen", "microsoft autogen"], "AutoGen"),
            "dify": ("Dify", ["github", "web"], "chinese", ["dify"], "Dify"),
            "mastra": ("Mastra", ["github", "web"], "international", ["mastra"], "Mastra"),
            "openhands": ("OpenHands", ["github", "web"], "international", ["openhands"], "OpenHands"),
            "qwen": ("Qwen", ["github", "huggingface", "web"], "chinese", ["qwen", "通义千问"], "Qwen"),
            "deepseek": ("DeepSeek", ["github", "huggingface", "web"], "chinese", ["deepseek"], "DeepSeek"),
            "openai": ("OpenAI", ["web"], "international", ["openai"], "OpenAI"),
            "anthropic": ("Anthropic", ["web"], "international", ["anthropic"], "Anthropic"),
            "ai agent": ("AI Agent", ["web"], "unknown", ["ai agent", "agentic ai"], None),
            "ai agent framework": (
                "AI Agent Framework",
                ["web"],
                "unknown",
                ["ai agent framework", "agent framework"],
                None,
            ),
        }

        for key, value in known.items():
            if key in lowered:
                entity_name, entity_scope, entity_origin, aliases, official_name = value
                resolved = ResolvedEntity(
                    name=entity_name,
                    entity_scope=entity_scope,
                    entity_origin=entity_origin,
                    aliases=aliases,
                    official_name=official_name,
                )
                print(
                    f"[实体解析] 规则命中 known 表: {name} → "
                    f"name={resolved.name}, scope={resolved.entity_scope}, "
                    f"origin={resolved.entity_origin}"
                )
                return resolved

        # 兜底：有代码相关关键词 → github + web，否则 → web
        entity_scope = (
            ["github", "web"]
            if any(kw in lowered for kw in ["github", "repo", "开源", "框架", "项目"])
            else ["web"]
        )

        resolved = ResolvedEntity(
            name=normalized,
            entity_scope=entity_scope,
            aliases=[lowered],
            official_name=normalized,
        )
        print(
            f"[实体解析] 规则兜底: {name} → "
            f"name={resolved.name}, scope={resolved.entity_scope}, "
            f"origin={resolved.entity_origin}"
        )
        return resolved
