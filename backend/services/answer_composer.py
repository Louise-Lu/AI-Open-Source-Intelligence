from __future__ import annotations

import json
from typing import Any, List

from llms.deepseek import deepseek_model
from schemas.composed_report import ComposedAnswer


class AnswerComposer:
    def __init__(self):
        self.llm = deepseek_model.with_structured_output(ComposedAnswer)
        
    def _serialize_evidences(self, evidences: List) -> List[dict]:
        """将 IntelligenceEvidence 对象转换为可 JSON 序列化的字典"""
        serialized = []
        for ev in evidences:
            if hasattr(ev, 'model_dump'):
                serialized.append(ev.model_dump())
            elif hasattr(ev, 'dict'):
                serialized.append(ev.dict())
            elif hasattr(ev, 'to_dict'):
                serialized.append(ev.to_dict())
            elif isinstance(ev, dict):
                serialized.append(ev)
            else:
                # 兜底方案
                serialized.append({"value": str(ev)})
        return serialized
    
    def compose(self, message: str, entity_dict: dict, evidences: list) -> ComposedAnswer:
        # 序列化证据
        serializable_evidences = self._serialize_evidences(evidences)
        
        # 提取实体名称
        entities = entity_dict.get("entities", [])
        entity_names = [e.get("name", "未知实体") for e in entities]
        entity_name_str = "、".join(entity_names) if entity_names else "未指定"

        prompt = f"""
    你是 AI 开源项目分析助手。

    根据已有的结构化分析结果回答用户。
    并给出依据。

    用户的问题：
    {message}

    涉及实体：
    {entity_name_str}

    证据详情：
    {json.dumps(serializable_evidences, ensure_ascii=False, indent=2)}


要求：

- 输出中文自然语言
- 像 ChatGPT 对话一样回答
- 不使用 Markdown 标题
- 不输出 JSON
- 不输出报告模板
- 不重复展示字段名
- 解释数据来源
- 只基于输入报告内容，不要编造数据
- 保持简洁
- 针对性回答用户的问题（不要泛泛而谈）


不要输出markdown格式：
例如：
# 项目分析
## Summary

""".strip()

        try:
            result = self.llm.invoke(prompt)
            if hasattr(result, "model_dump"):
                return result
            return ComposedAnswer.model_validate(result)
        except Exception as exc:
            print(f"AnswerComposer fallback: {exc}")
            # return ComposedAnswer(answer=self._fallback_answer(entity_name, evidence))

    # @staticmethod
    # def _fallback_answer(project_name: str, reports: dict[str, Any]) -> str:
    #     parts = [f"项目：{project_name}"]
    #     for key, value in reports.items():
    #         if isinstance(value, dict):
    #             parts.append(f"{key}：{json.dumps(value, ensure_ascii=False, indent=2)}")
    #         else:
    #             parts.append(f"{key}：{value}")
    #     return "\n\n".join(parts)
