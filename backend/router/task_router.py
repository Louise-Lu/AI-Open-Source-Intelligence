# 两级路由架构：LLM 先判任务Task → 任务映射固定功能列表 → 每个功能再映射到固定工具集。
# 这本质上是一种确定性工作流，而非 Agent 自主规划
# 但

from __future__ import annotations

from llms.deepseek import deepseek_model
from prompts.task import TASK_PROMPT
from schemas.task import TaskRoute


class TaskRouter:
    def __init__(self):
        self.llm = deepseek_model.with_structured_output(TaskRoute)

    def route(self, query: str) -> dict:
        prompt = f"""
{TASK_PROMPT}

用户问题:
{query}
"""
        try:
            result = self.llm.invoke(prompt)
            # print(result)
            return result.model_dump() if hasattr(result, "model_dump") else dict(result)
        except Exception as exc:
            print(f"TaskRouter fallback: {exc}")
            # return self._rule_based_route(query)

    @staticmethod
    def _rule_based_route(query: str) -> dict:
        text = query.lower()

        if any(keyword in text for keyword in ["比较", "对比", "compare"]):
            return {
                "task": "project_comparison",
                "reports": ["comparison"],
            }

        if any(keyword in text for keyword in ["更新", "release", "版本", "变更", "diff"]):
            return {
                "task": "update_tracking",
                "reports": ["release_diff"],
            }

        if any(keyword in text for keyword in ["未来", "发展", "roadmap", "趋势", "下一步", "未来三个月", "未来发展方向"]):
            return {
                "task": "single_project_analysis",
                "reports": ["roadmap"],
            }

        if any(keyword in text for keyword in ["分析", "怎么样", "是什么", "介绍", "值不值得", "值得", "好不好", "评价"]):
            return {
                "task": "single_project_analysis",
                "reports": ["profile", "analysis"],
            }

        # if any(keyword in text for keyword in ["搜索", "查找", "找一下", "有哪些"]):
        #     return {
        #         "task": "deep_search",
        #         "reports": [],
        #     }

        return {
            "task": "general_question",
            "reports": [],
        }
