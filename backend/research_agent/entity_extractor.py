from __future__ import annotations

import logging

from llms.deepseek import deepseek_model
from shared_schemas.entity import EntityExtraction

logger = logging.getLogger(__name__)

EXTRACTOR_PROMPT = """从用户问题中提取技术相关实体。
实体包括：开源项目、AI模型、公司、产品、框架、工具、技术概念。

规则：
1. 用户提到任何具体名称，都必须返回。
2. 不判断任务类型。
3. 不猜测 github owner/repo。
4. 不猜测 HuggingFace model id。

输出 JSON:
{"entities":[{"name":"xxx"}]}
"""


class EntityExtractor:
    def __init__(self):
        self.llm = deepseek_model.with_structured_output(EntityExtraction)

    def extract(self, query: str) -> dict:
        prompt = f"""
{EXTRACTOR_PROMPT}

用户问题:
{query}
"""
        try:
            result = self.llm.invoke(prompt)
            return result.model_dump() if hasattr(result, "model_dump") else dict(result)
        except Exception as exc:
            logger.warning("EntityExtractor fallback: %s", exc)
            return self._rule_based_extract(query)

    @staticmethod
    def _rule_based_extract(query: str) -> dict:
        text = query.lower()
        entities: list[dict[str, str]] = []

        known_projects = [
            ("langgraph", {"name": "LangGraph"}),
            ("crewai", {"name": "CrewAI"}),
            ("autogen", {"name": "AutoGen"}),
            ("dify", {"name": "dify"}),
            ("qwen", {"name": "Qwen"}),
            ("llama", {"name": "Llama"}),
            ("deepseek", {"name": "DeepSeek"}),
            ("langchain", {"name": "LangChain"}),
            ("openai", {"name": "OpenAI"}),
            ("anthropic", {"name": "Anthropic"}),
        ]

        for keyword, project in known_projects:
            if keyword in text:
                entities.append(project)

        if not entities:
            entities.append({"name": query.strip()[:80]})

        return {"entities": entities}
