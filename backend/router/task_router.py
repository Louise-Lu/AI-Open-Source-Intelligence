from __future__ import annotations

import re

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
你是一个任务路由器。
只判断用户想执行什么任务，不要解析 repo，也不要抽取实体。

可选 route:
- profile
- roadmap
- comparison
- release_diff
- analysis_report
- agent

用户问题：
{query}

只返回结构化结果。
""".strip()

    @staticmethod
    def _rule_based_route(query: str) -> dict:
        text = query.lower()

        if any(keyword in text for keyword in ["比较", "对比", "compare"]):
            route = "comparison"
        elif any(keyword in text for keyword in ["未来三个月", "未来发展", "路线", "roadmap", "下一步"]):
            route = "roadmap"
        elif any(keyword in text for keyword in ["分析一下", "帮我分析", "analysis", "分析报告", "报告"]):
            route = "analysis_report"
        elif any(keyword in text for keyword in ["release", "版本", "更新", "最近版本", "diff"]):
            route = "release_diff"
        elif any(keyword in text for keyword in ["是什么", "介绍", "项目是什么", "技术栈", "profile"]):
            route = "profile"
        else:
            route = "agent"

        return {
            "route": route,
            "reason": "rule-based fallback",
        }
