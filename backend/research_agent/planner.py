# planner.py — Research Goal Planner
#
# 职责: 根据 ResearchIntent + Entity 生成 Goal 驱动的 ResearchGoal
# 输入: ResearchIntent + list[ResolvedEntity]
# 输出: ResearchGoal { objective, user_goal, entities, context, depth,
#                      success_criteria, constraints }
#
# Planner 不负责：
# - 工具规划
# - 研究问题拆分
# - 数据源选择
# 这些全部由 ReAct Agent 自主决定。

from __future__ import annotations

import json
import logging

from llms.deepseek import deepseek_model
from research_agent.schemas.research import ResearchGoal, ResearchIntent
from shared_schemas.entity import ResolvedEntity

logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """你是 AI Intelligence Research Agent 的研究规划器。

## 核心职责
根据用户的研究意图和已解析实体，生成一个 Goal 驱动的研究目标。生成中文。

你只定义"要完成什么"，不定义"怎么完成"。
不要生成研究问题、不要生成执行步骤、不要选择数据源、不要选择工具。
工具调用顺序、数据源选择和探索深度由后续 ReAct Agent 自主决定。

## 输出字段说明

### objective
直接使用意图中的 objective 类型。

### user_goal
一句自然语言，描述用户想通过这次研究达成什么。
例如："评估 CrewAI 是否适合作为多智能体编排框架"

### context
一句背景信息，帮助 Agent 理解用户的研究处境。
例如："用户正在选型 AI Agent 框架，关注社区活跃度和维护风险"

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
  "context": "用户正在选型 AI Agent 框架，关注社区活跃度和维护风险",
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

现在，请根据以下研究意图和实体信息生成研究目标，只输出 JSON。
"""


class ResearchAgentPlanner:
    """根据 ResearchIntent + Entity 生成 Goal 驱动的 ResearchGoal。

    Planner 只负责定义研究目标和完成标准，不负责决定工具调用顺序。
    """

    def __init__(self):
        self.llm = deepseek_model.with_structured_output(ResearchGoal)

    def plan(
        self,
        intent: ResearchIntent,
        entities: list[ResolvedEntity],
    ) -> ResearchGoal:
        """生成研究目标。

        如果 entities 为空，直接返回 need_user_input 状态。
        """
        # Entity Guard: 没有解析到实体时不生成计划
        if not entities:
            return ResearchGoal(
                objective=intent.objective,
                user_goal="",
                entities=[],
                context="",
                depth=intent.depth,
                success_criteria=[],
                constraints=[],
                status="need_user_input",
                message="未识别到需要研究的对象，请提供项目名称或 GitHub Repository。",
            )

        if intent.depth == "quick":
            return self._quick_plan(intent, entities)

        try:
            goal = self._llm_plan(intent, entities)
        
        except Exception as exc:
            logger.warning("ResearchAgentPlanner LLM error, using fallback: %s", exc)
            goal = self._quick_plan(intent, entities)

        return goal

    # ── LLM Planning ──────────────────────────────────────────

    def _llm_plan(
        self,
        intent: ResearchIntent,
        entities: list[ResolvedEntity],
    ) -> ResearchGoal:
        entity_info = [
            {
                "name": e.name,
                "entity_type": e.entity_type,
                "aliases": e.aliases,
                "official_name": e.official_name,
            }
            for e in entities
        ]

        prompt = f"""{PLANNER_SYSTEM_PROMPT}

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

    # ── Quick Goal (Fallback) ──────────────────────────────────

    def _quick_plan(
        self,
        intent: ResearchIntent,
        entities: list[ResolvedEntity],
    ) -> ResearchGoal:
        """快速模式：根据 objective 类型生成精简研究目标。"""
        entity_names = [e.name for e in entities] or intent.entities
        entity_label = "、".join(entity_names or ["目标对象"])

        strategies = {
            "trend_analysis": {
                "user_goal": f"分析 {entity_label} 最近的发展趋势",
                "context": f"用户希望了解 {entity_label} 近期的技术演进和社区动态",
                "success_criteria": [
                    "已识别近期主要技术方向",
                    "已找到代表性项目或事件",
                    "已总结社区关注点",
                    "已形成趋势判断",
                ],
            },
            "evaluation": {
                "user_goal": f"评估 {entity_label} 的整体状况",
                "context": f"用户希望了解 {entity_label} 的技术能力、社区健康度和风险",
                "success_criteria": [
                    "已识别项目的核心定位和技术架构",
                    "已评估社区活跃度和维护健康度",
                    "已总结主要风险和适用场景",
                ],
            },
            "comparison": {
                "user_goal": f"对比分析 {entity_label} 的差异和取舍",
                "context": f"用户正在比较 {entity_label}，需要理解各自的优势和劣势",
                "success_criteria": [
                    "已明确各实体的核心定位和差异",
                    "已从活跃度、生态、风险等维度对比",
                    "已形成取舍建议",
                ],
            },
            "technology_research": {
                "user_goal": f"深入研究 {entity_label} 的技术原理和架构",
                "context": f"用户希望理解 {entity_label} 的技术实现和典型用法",
                "success_criteria": [
                    "已理解核心技术原理和架构设计",
                    "已找到典型用法和实践案例",
                    "已识别技术限制和注意事项",
                ],
            },
            "market_research": {
                "user_goal": f"研究 {entity_label} 所在方向的市场机会",
                "context": f"用户希望了解 {entity_label} 的市场格局和机会",
                "success_criteria": [
                    "已了解市场需求和竞争格局",
                    "已识别主要参与者和定位",
                    "已评估机会和风险",
                ],
            },
            "information_lookup": {
                "user_goal": f"了解 {entity_label} 是什么",
                "context": f"用户希望快速了解 {entity_label} 的基本信息",
                "success_criteria": [
                    "已明确对象的定义和核心定位",
                    "已了解主要能力和使用场景",
                ],
            },
            "decision_support": {
                "user_goal": f"为 {entity_label} 的选型提供决策支持",
                "context": f"用户正在做技术选型，需要基于证据做决策",
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

        return ResearchGoal(
            objective=intent.objective,
            user_goal=strategy["user_goal"],
            entities=entity_names,
            context=strategy["context"],
            depth=intent.depth,
            success_criteria=strategy["success_criteria"],
            constraints=[
                "优先官方来源",
                "不要猜测",
                "多个来源交叉验证",
                "证据不足时明确说明",
            ],
        )
