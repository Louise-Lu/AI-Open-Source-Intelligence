from __future__ import annotations

from llms.deepseek import deepseek_model
from prompts.entityextractor import EXTRACTOR_PROMPT
from schemas.entity import EntityExtraction


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
            print(f"EntityExtractor fallback: {exc}")
            # return self._rule_based_extract(query)

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
        ]

        for keyword, project in known_projects:
            if keyword in text:
                entities.append(project)

        if not entities:
            if "langchain" in text:
                entities.append({"name": "LangGraph"})
            elif "qwen" in text or "llama" in text or "deepseek" in text:
                entities.append({"name": query.strip()})
            else:
                entities.append({"name": query.strip()})

        return {"entities": entities}
