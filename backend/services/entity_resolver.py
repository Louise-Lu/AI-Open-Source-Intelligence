from __future__ import annotations

from typing import Any

from config.entity_mapping import ENTITY_MAPPING
from llms.deepseek import deepseek_model
from schemas.entity import EntitySource, ExtractedEntity, ResolvedEntity


class EntityResolver:
    def __init__(self):
        self.llm = deepseek_model.with_structured_output(ResolvedEntity)

    def resolve(self, entity: ExtractedEntity | dict[str, Any] | str) -> ResolvedEntity:
        name = self._extract_name(entity)
        # print("resolved_entity",name)
        
        if not name:
            return ResolvedEntity(name="", sources=[])

        mapping = self._match_mapping(name)
        if mapping is not None:
            return ResolvedEntity(name=name, sources=mapping)

        try:
            inferred = self._llm_resolve(name)
            if inferred:
                return inferred
        except Exception as exc:
            print(f"EntityResolver fallback: {exc}")

        return ResolvedEntity(name=name, sources=[])

    @staticmethod
    def _extract_name(entity: ExtractedEntity | dict[str, Any] | str) -> str:
        if isinstance(entity, str):
            return entity.strip()
        if isinstance(entity, ExtractedEntity):
            return entity.name.strip()
        return str(entity.get("name", "")).strip()

    @staticmethod
    def _normalize(text: str) -> str:
        return text.strip().lower()

    def _match_mapping(self, name: str) -> list[EntitySource] | None:
        lowered = self._normalize(name)
        for key, value in ENTITY_MAPPING.items():
            if key in lowered:
                return [EntitySource(**source) for source in value.get("sources", [])]
        if "langchain" in lowered:
            return [EntitySource(source="github", identifier="langchain-ai/langgraph")]
        return None

    def _llm_resolve(self, name: str) -> ResolvedEntity | None:
        prompt = f"""
根据实体名称判断它可用的数据源。

输出 JSON:
{{
  "name": "{name}",
  "sources": [
    {{"source": "github", "identifier": "owner/repo"}},
    {{"source": "huggingface", "identifier": "org/model"}}
  ]
}}

规则：
1. 不要编造 source。
2. 不确定时 sources 返回空数组。
3. 只输出 JSON。

实体名称:
{name}
"""
        result = self.llm.invoke(prompt)
        payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        sources = [
            EntitySource(**source)
            for source in payload.get("sources", []) or []
            if source.get("source") and source.get("identifier")
        ]
        return ResolvedEntity(name=payload.get("name") or name, sources=sources)
