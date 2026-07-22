from __future__ import annotations

from llms.deepseek import deepseek_model
from schemas.task import TaskRoute


class TaskRouter:
    def __init__(self):
        self.llm = deepseek_model.with_structured_output(TaskRoute)

    def route(self, query: str) -> dict:
        prompt = self._build_prompt(query)
        try:
            result = self.llm.invoke(prompt)
            return result.model_dump() if hasattr(result, "model_dump") else dict(result)
        except Exception as exc:
            print(f"TaskRouter fallback: {exc}")
            return self._rule_based_route(query)

    @staticmethod
    def _build_prompt(query: str) -> str:
        return f"""
你是 AI 开源情报系统任务路由器。

你的职责：
1. 判断用户想完成什么任务
2. 判断需要生成哪些报告

不要：
- 提取项目名称
- 判断 GitHub owner/repo
- 选择具体工具

Task:
- single_project_analysis
- project_comparison
- project_search
- update_tracking
- general_question

Reports:
- profile
- project_health
- analysis
- roadmap
- comparison
- recommendation
- release_diff

只返回 JSON。

路由示例：
- "LangGraph怎么样" -> {{"task":"single_project_analysis","reports":["profile","analysis"],"need_entity_resolution":true}}
- "LangGraph未来发展趋势" -> {{"task":"single_project_analysis","reports":["roadmap"],"need_entity_resolution":true}}
- "比较LangGraph和CrewAI" -> {{"task":"project_comparison","reports":["comparison"],"need_entity_resolution":true}}
- "CrewAI怎么样" -> {{"task":"single_project_analysis","reports":["profile","analysis"],"need_entity_resolution":true}}

用户问题：
{query}
""".strip()

    @staticmethod
    def _rule_based_route(query: str) -> dict:
        text = query.lower()

        if any(keyword in text for keyword in ["比较", "对比", "compare"]):
            return {
                "task": "project_comparison",
                "reports": ["comparison"],
                "need_entity_resolution": True,
                "confidence": 0.95,
            }

        if any(keyword in text for keyword in ["更新", "release", "版本", "变更", "diff"]):
            return {
                "task": "update_tracking",
                "reports": ["release_diff"],
                "need_entity_resolution": True,
                "confidence": 0.9,
            }

        if any(keyword in text for keyword in ["未来", "发展", "roadmap", "趋势", "下一步", "未来三个月", "未来发展方向"]):
            return {
                "task": "single_project_analysis",
                "reports": ["roadmap"],
                "need_entity_resolution": True,
                "confidence": 0.92,
            }

        if any(keyword in text for keyword in ["分析", "怎么样", "是什么", "介绍", "值不值得", "值得", "好不好", "评价"]):
            return {
                "task": "single_project_analysis",
                "reports": ["profile", "analysis"],
                "need_entity_resolution": True,
                "confidence": 0.9,
            }

        if any(keyword in text for keyword in ["搜索", "查找", "找一下", "有哪些"]):
            return {
                "task": "project_search",
                "reports": [],
                "need_entity_resolution": True,
                "confidence": 0.85,
            }

        return {
            "task": "general_question",
            "reports": [],
            "need_entity_resolution": False,
            "confidence": 0.7,
        }
