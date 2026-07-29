# context_builder.py — Research Context Builder
#
# 职责: 根据 ResearchIntent + Entity 构建 ResearchContext
# 输入: ResearchIntent + list[ResolvedEntity]
# 输出: ResearchContext { objective, user_goal, entities, focus, time_range, depth,
#                       research_brief, success_criteria, constraints }
#
# ResearchContextBuilder 不负责：
# - 工具规划
# - 研究问题拆分
# - 数据源选择
# 这些全部由 ReAct Agent 自主决定。

from __future__ import annotations

import json

from llms.deepseek import deepseek_model
from research_agent.schemas.research import ResearchContext, ResearchIntent
from shared_schemas.entity import ResolvedEntity



CONTEXT_BUILDER_SYSTEM_PROMPT = """你是 AI Intelligence Research Agent 的研究上下文构建器。

## 核心职责
根据用户的研究意图和已解析实体，构建一个 ResearchContext。生成中文。

你只回答"用户真正想研究什么"，不定义"怎么研究"。
不要生成研究问题、不要生成执行步骤、不要选择数据源、不要选择工具。
是否需要 GitHub / Community / RSS / YouTube / HuggingFace、工具调用顺序、Discovery 次数和是否结束研究，都由后续 ReAct Agent 自主决定。

## 输出字段说明

### objective
直接使用意图中的 objective 类型。

### user_goal
一句自然语言，描述用户想通过这次研究达成什么。
例如："评估 CrewAI 是否适合作为多智能体编排框架"

### focus
直接透传意图中的 focus，不要重新解析或修改。
例如：["community", "sentiment"]

### time_range
直接透传意图中的 time_range，不要重新解析或修改。
例如：recent / latest / historical / future / any

### research_brief
给 Agent 的研究说明，解释研究重点、需要关注的具体维度以及注意事项。
不要只写一句背景，要写清楚 Agent 在这次研究中应该重点关注什么。
例如：
"请重点关注：
1. Twitter 和 Reddit 社区讨论。
2. 最近版本是否影响社区评价。
3. 总结积极观点、负面观点及主要争议。
不要只总结 GitHub README。"

### depth
直接使用意图中的 depth。

### success_criteria
2-5 条可验证的完成标准。告诉 Agent 什么时候算研究完成。
不要写成问题，写成"已达成"的状态。
例如：["已识别项目的核心定位和技术架构", "已评估社区活跃度和维护健康度", "已总结主要风险和适用场景"]

### constraints
2-4 条研究约束。
例如：["优先官方来源", "不要猜测", "证据不足时明确说明"]

## 输出格式 — 严格 JSON

{
  "objective": "evaluation",
  "user_goal": "评估 CrewAI 是否适合作为多智能体编排框架",
  "entities": ["CrewAI"],
  "focus": ["community", "sentiment"],
  "time_range": "recent",
  "research_brief": "请重点关注：\n1. 社区活跃度和维护健康度。\n2. 技术架构和核心定位。\n3. 主要风险和适用场景。\n不要只总结 GitHub README。",
  "depth": "standard",
  "success_criteria": [
    "已识别项目的核心定位和技术架构",
    "已评估社区活跃度和维护健康度",
    "已总结主要风险和适用场景"
  ],
  "constraints": [
    "优先官方来源",
    "不要猜测",
    "证据不足时明确说明"
  ]
}

---

现在，请根据以下研究意图和实体信息构建 ResearchContext，只输出 JSON。
"""


class ResearchContextBuilder:
    """根据 ResearchIntent + Entity 构建 ResearchContext。

    ResearchContextBuilder 只负责定义用户真正想研究什么，不负责决定工具调用顺序、数据源或执行步骤。
    """

    def __init__(self):
        self.llm = deepseek_model.with_structured_output(ResearchContext)

    def build(
        self,
        intent: ResearchIntent,
        entities: list[ResolvedEntity],
    ) -> ResearchContext | None:
        """构建研究上下文。

        如果 entities 为空，返回 None，由调用方处理 need_user_input。
        """
        # Entity Guard: 没有解析到实体时不构建研究上下文
        if not entities:
            return None

        if intent.depth == "quick":
            return self._quick_build(intent, entities)

        try:
            research_context = self._llm_build(intent, entities)
        except Exception:
            research_context = self._quick_build(intent, entities)

        return research_context

    # ── LLM Context Building ───────────────────────────────────

    def _llm_build(
        self,
        intent: ResearchIntent,
        entities: list[ResolvedEntity],
    ) -> ResearchContext:
        entity_info = [
            {
                "name": e.name,
                "entity_type": e.entity_type,
                "aliases": e.aliases,
                "official_name": e.official_name,
            }
            for e in entities
        ]

        prompt = f"""{CONTEXT_BUILDER_SYSTEM_PROMPT}

## 研究意图
- 目标类型: {intent.objective}
- 实体: {json.dumps(intent.entities, ensure_ascii=False)}
- 关注维度: {json.dumps(intent.focus, ensure_ascii=False)}
- 时间范围: {intent.time_range}
- 深度: {intent.depth}
- 原始查询: {intent.raw_query}

## 已解析实体
{json.dumps(entity_info, ensure_ascii=False, indent=2)}
"""
        return self.llm.invoke(prompt)

    # ── Quick Context (Fallback) ────────────────────────────────

    def _quick_build(
        self,
        intent: ResearchIntent,
        entities: list[ResolvedEntity],
    ) -> ResearchContext:
        """快速模式：根据 objective 类型生成精简研究上下文。"""
        entity_names = [e.name for e in entities] or intent.entities
        entity_label = "、".join(entity_names or ["目标对象"])

        strategies = {
            "trend_analysis": {
                "user_goal": f"分析 {entity_label} 最近的发展趋势",
                "research_brief": f"请重点关注：\n1. {entity_label} 近期的技术演进和社区动态。\n2. Twitter 和 Reddit 上的社区讨论。\n3. 积极观点和负面观点。\n不要只总结 GitHub README。",
                "success_criteria": [
                    "已识别近期主要技术方向",
                    "已找到代表性项目或事件",
                    "已总结社区关注点",
                    "已形成趋势判断",
                ],
            },
            "evaluation": {
                "user_goal": f"评估 {entity_label} 的整体状况",
                "research_brief": f"请重点关注：\n1. {entity_label} 的技术能力、社区健康度和风险。\n2. Twitter 和 Reddit 社区讨论。\n3. 最近版本是否影响社区评价。\n4. 总结积极观点、负面观点及主要争议。\n不要只总结 GitHub README。",
                "success_criteria": [
                    "已识别项目的核心定位和技术架构",
                    "已评估社区活跃度和维护健康度",
                    "已总结主要风险和适用场景",
                ],
            },
            "comparison": {
                "user_goal": f"对比分析 {entity_label} 的差异和取舍",
                "research_brief": f"请重点关注：\n1. {entity_label} 各自的优势和劣势。\n2. 社区讨论中的评价和争议。\n3. 多源交叉验证，不要只依赖 GitHub。",
                "success_criteria": [
                    "已明确各实体的核心定位和差异",
                    "已从活跃度、生态、风险等维度对比",
                    "已形成取舍建议",
                ],
            },
            "technology_research": {
                "user_goal": f"深入研究 {entity_label} 的技术原理和架构",
                "research_brief": f"请重点关注：\n1. {entity_label} 的技术实现原理和架构设计。\n2. 社区中的典型用法和实践案例。\n3. 技术限制和注意事项。\n不要只总结官方文档。",
                "success_criteria": [
                    "已理解核心技术原理和架构设计",
                    "已找到典型用法和实践案例",
                    "已识别技术限制和注意事项",
                ],
            },
            "market_research": {
                "user_goal": f"研究 {entity_label} 所在方向的市场机会",
                "research_brief": f"请重点关注：\n1. {entity_label} 的市场格局和竞争态势。\n2. Twitter 和 Reddit 上的行业讨论和趋势。\n3. 机会和风险评估。\n不要只总结 GitHub。",
                "success_criteria": [
                    "已了解市场需求和竞争格局",
                    "已识别主要参与者和定位",
                    "已评估机会和风险",
                ],
            },
            "information_lookup": {
                "user_goal": f"了解 {entity_label} 是什么",
                "research_brief": f"请重点关注：\n1. {entity_label} 的核心定位和基本信息。\n2. 主要能力和使用场景。\n不要只总结 GitHub README。",
                "success_criteria": [
                    "已明确对象的定义和核心定位",
                    "已了解主要能力和使用场景",
                ],
            },
            "decision_support": {
                "user_goal": f"为 {entity_label} 的选型提供决策支持",
                "research_brief": f"请重点关注：\n1. {entity_label} 的技术能力和适配度。\n2. Twitter 和 Reddit 社区评价和争议。\n3. 主要风险和取舍。\n不要只总结 GitHub README。",
                "success_criteria": [
                    "已评估技术能力和适配度",
                    "已识别主要风险和取舍",
                    "已形成明确的推荐或建议",
                ],
            },
        }

        strategy = strategies.get(
            intent.objective, strategies["information_lookup"]
        )

        return ResearchContext(
            objective=intent.objective,
            user_goal=strategy["user_goal"],
            entities=entity_names,
            focus=intent.focus,
            time_range=intent.time_range,
            research_brief=strategy["research_brief"],
            depth=intent.depth,
            success_criteria=strategy["success_criteria"],
            constraints=[
                "优先官方来源",
                "不要猜测",
                "多个来源交叉验证",
                "证据不足时明确说明",
            ],
        )
