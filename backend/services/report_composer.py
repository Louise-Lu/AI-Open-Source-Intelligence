from __future__ import annotations

import json
from typing import Any

from llms.deepseek import deepseek_model
from schemas.composed_report import ComposedAnswer


class ReportComposer:
    def __init__(self):
        self.llm = deepseek_model.with_structured_output(ComposedAnswer)

    def compose(self, message: str, project_name: str, reports: dict[str, Any]) -> ComposedAnswer:
        prompt = f"""
你是 AI 开源项目分析助手。

根据已有的结构化分析结果回答用户。

用户的问题：
{message}

project:
{project_name}

reports:
{json.dumps(reports, ensure_ascii=False, indent=2)}


要求：

- 输出中文自然语言
- 像 ChatGPT 对话一样回答
- 不使用 Markdown 标题
- 不输出 JSON
- 不输出报告模板
- 不重复展示字段名
- 不解释数据来源
- 只基于输入报告内容，不要编造数据
- 保持简洁
- 针对性回答用户的问题（不要泛泛而谈）

例如输出：

"这个项目主要用于...
从技术定位来看...
如果你关注企业应用，需要注意..."


不要输出：

# 项目分析

## Summary

""".strip()

        try:
            result = self.llm.invoke(prompt)
            if hasattr(result, "model_dump"):
                return result
            return ComposedAnswer.model_validate(result)
        except Exception as exc:
            print(f"ReportComposer fallback: {exc}")
            return ComposedAnswer(answer=self._fallback_answer(project_name, reports))

    @staticmethod
    def _fallback_answer(project_name: str, reports: dict[str, Any]) -> str:
        parts = [f"项目：{project_name}"]
        for key, value in reports.items():
            if isinstance(value, dict):
                parts.append(f"{key}：{json.dumps(value, ensure_ascii=False, indent=2)}")
            else:
                parts.append(f"{key}：{value}")
        return "\n\n".join(parts)
