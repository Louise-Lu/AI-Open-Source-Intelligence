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

#     @staticmethod
#     def _build_prompt(query: str) -> str:
#         return f"""
# 从用户问题中提取项目名称。
# 只负责识别项目名字。
# 不要猜测 GitHub owner/repo。
# 输出 projects 数组。

# 用户问题：
# {query}
# """.strip()

    # @staticmethod
    # def _rule_based_extract(query: str) -> dict:
    #     text = query.lower()
    #     projects: list[dict[str, str]] = []

    #     known_projects = [
    #         ("langgraph", {"name": "LangGraph"}),
    #         ("crewai", {"name": "CrewAI"}),
    #         ("autogen", {"name": "AutoGen"}),
    #         ("dify", {"name": "dify"}),
    #     ]

    #     for keyword, project in known_projects:
    #         if keyword in text:
    #             projects.append(project)

    #     if not projects:
    #         if "langgraph" in text or "langchain" in text:
    #             projects.append({"name": "LangGraph"})
    #         elif "crewai" in text:
    #             projects.append({"name": "CrewAI"})

    #     if len(projects) == 0:
    #         return {"projects": []}

    #     if len(projects) > 2:
    #         projects = projects[:2]

    #     return {"projects": projects}
