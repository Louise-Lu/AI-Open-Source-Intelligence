# ExtractedEntity -> ResolvedEntity（系统理解后的实体）
# 应该包含：这个东西是谁 它在哪里 有哪些来源

# example
# ResolvedEntity(
#     name="Qwen",

#     sources=[
#         EntitySource(
#             source="github",
#             identifier="QwenLM/Qwen"
#         ),

#         EntitySource(
#             source="huggingface",
#             identifier="Qwen/Qwen2.5-7B"
#         )
#     ]
# )

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
        
        if not name:
            return ResolvedEntity(name="", sources=[])

        # mapping = self._match_mapping(name)
        # if mapping is not None:
        #     return ResolvedEntity(name=name, sources=mapping)

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
    请根据实体名称 "{name}"，尽可能推断它在以下平台的位置：

    1. GitHub (格式: owner/repo)
    2. HuggingFace (格式: org/model)

    **规则：**
    - 如果能确定 GitHub 仓库，必须返回 github 源。
    - 如果能确定 HuggingFace 模型，必须返回 huggingface 源。
    - 如果不确定，宁可不返回该源，不要瞎编。
    - 如果完全不知道，返回空 sources。
    
    **重要**：必须使用最知名、最活跃的官方主仓库，不要缩写名称。
    例如：deepseek → deepseek-ai/DeepSeek-V3（而不是 deepseek-ai/deepseek）
    Qwen → QwenLM/Qwen（而不是 Qwen）

    输出 JSON:
    {{
    "name": "{name}",
    "sources": [
        {{"source": "github", "identifier": "..."}},
        {{"source": "huggingface", "identifier": "..."}}
    ]
    }}
"""
        result = self.llm.invoke(prompt)
        payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        sources = [
            EntitySource(**source)
            for source in payload.get("sources", []) or []
            if source.get("source") and source.get("identifier")
        ]
        return ResolvedEntity(name=payload.get("name") or name, sources=sources)
