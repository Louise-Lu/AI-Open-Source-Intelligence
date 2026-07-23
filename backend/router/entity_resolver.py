# ExtractedEntity -> ResolvedEntity（系统理解后的实体）
# 应该包含：这个东西是谁 它在哪里 有哪些来源

# Entity Resolver
#       |
#       |
#       +-- Known Entity DB
#       |
#       +-- Github Search API
#       |
#       +-- HuggingFace Search API
#       |
#       +-- LLM Ranking

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

# from config.entity_mapping import ENTITY_MAPPING
from sources.github.client import GitHubAPI
from sources.huggingface.client import HuggingFaceClient

from llms.deepseek import deepseek_model
from schemas.entity import EntitySource, ExtractedEntity, ResolvedEntity


class EntityResolver:
    def __init__(self):
        self.llm = deepseek_model.with_structured_output(ResolvedEntity)
        self.github = GitHubAPI()
        self.hf_client = HuggingFaceClient()

    def resolve(self, entity: ExtractedEntity | dict[str, Any] | str) -> ResolvedEntity:
        name = self._extract_name(entity)
        
        if not name:
            return ResolvedEntity(name="", sources=[])

        # mapping = self._match_mapping(name)
        # if mapping is not None:
        #     return ResolvedEntity(name=name, sources=mapping)

        sources = []

        # 1. 搜索 GitHub
        github_source = self._search_github(name)
        if github_source:
            sources.append(github_source)

        # 2. 搜索 HuggingFace
        hf_source = self._search_huggingface(name)
        if hf_source:
            sources.append(hf_source)

        print("搜索到的资源",sources)
        # 3. 如果搜索结果为空，使用 LLM 作为备选
        if not sources:
            llm_result = self._llm_resolve(name)
            if llm_result and llm_result.sources:
                return llm_result

        return ResolvedEntity(name=name, sources=sources)


    def _search_github(self, entity_name: str) -> EntitySource | None:
        """通过 GitHub API 搜索仓库"""
        try:
            response = self.github.client.get(
                "/search/repositories",
                params={
                    "q": entity_name,
                    "per_page": 5,
                },
            )
            payload: dict[str, Any] = response.json()
            items = payload.get("items") or []

            if not items:
                return None

            lowered = entity_name.strip().lower()

            # 优先精确匹配
            for item in items:
                name = (item.get("name") or "").lower()
                full_name = (item.get("full_name") or "").lower()
                if name == lowered or full_name.endswith(f"/{lowered}"):
                    return EntitySource(source="github", identifier=full_name)

            # 若无精确匹配，取第一个结果
            first = items[0]
            full_name = first.get("full_name")
            if full_name:
                return EntitySource(source="github", identifier=full_name)

            return None

        except Exception as e:
            print(f"github search error: {e}")
            return None


    def _search_huggingface(self, entity_name: str) -> EntitySource | None:
        """
        利用 HuggingFaceClient 的 session 和 BASE_URL 搜索模型。
        端点：/api/models?search={query}&limit=5&sort=downloads&direction=-1
        """
        try:
            url = f"{self.hf_client.BASE_URL}/api/models"
            params = {
                "search": entity_name,
                "limit": 5,
                "sort": "downloads",
                "direction": -1,
            }
            response = self.hf_client.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            items = response.json()
            if not items:
                return None

            # 返回第一个模型的 ID（格式: owner/model_name）
            first = items[0]
            model_id = first.get("id")
            if model_id:
                return EntitySource(source="huggingface", identifier=model_id)
            return None

        except Exception as e:
            print(f"HuggingFace search error: {e}")
            return None

    def _llm_resolve(self, name: str) -> ResolvedEntity | None:
        """使用 LLM 推理实体来源（备选方案）"""
        prompt = f"""
    请根据实体名称 "{name}"，尽可能推断它在以下平台的位置：

    1. GitHub (格式: owner/repo)
    2. HuggingFace (格式: org/model)

    **规则：**
    - 如果能确定 GitHub 仓库，必须返回 github 源。
    - 如果能确定 HuggingFace 模型，必须返回 huggingface 源。
    - 如果完全不知道，返回空 sources。

    **重要**：必须使用最知名、最活跃的官方主仓库，不要缩写名称。
    # 例如：deepseek → deepseek-ai/DeepSeek-V3（而不是 deepseek-ai/deepseek）
    # Qwen → QwenLM/Qwen（而不是 Qwen）

    输出 JSON:
    {{
        "name": "{name}",
        "sources": [
            {{"source": "github", "identifier": "..."}},
            {{"source": "huggingface", "identifier": "..."}}
        ]
    }}
    """
        try:
            response = self.llm.invoke(prompt)
            payload = response.model_dump() if hasattr(response, "model_dump") else dict(response)
            sources = [
                EntitySource(**source)
                for source in payload.get("sources", []) or []
                if source.get("source") and source.get("identifier")
            ]
            return ResolvedEntity(name=payload.get("name") or name, sources=sources)
        except Exception as e:
            print(f"LLM resolve error: {e}")
            return None


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

    # def _match_mapping(self, name: str) -> list[EntitySource] | None:
    #     lowered = self._normalize(name)
    #     for key, value in ENTITY_MAPPING.items():
    #         if key in lowered:
    #             return [EntitySource(**source) for source in value.get("sources", [])]
    #     if "langchain" in lowered:
    #         return [EntitySource(source="github", identifier="langchain-ai/langgraph")]
    #     return None
