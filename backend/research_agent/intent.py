# intent.py — Research Goal Understanding
#
# 职责: 理解用户真正的研究目标
# 输入: 用户原始 query
# 输出: ResearchIntent { objective, entities, focus, time_range, depth, raw_query }
#
# 注意：IntentRouter 不是任务分类器，不生成报告，不选择工具，不规划步骤。

from __future__ import annotations

import logging
import re

from llms.deepseek import deepseek_model
from research_agent.schemas.research import ResearchIntent

logger = logging.getLogger(__name__)


INTENT_SYSTEM_PROMPT = """你是 AI Intelligence Research Agent 的研究目标理解器。

## 核心职责
理解用户真正的研究目标，输出结构化的 ResearchIntent JSON。

你不是任务分类器。你的职责不是决定执行哪个 Pipeline，也不是规划步骤，而是理解：
- 用户想了解什么对象
- 用户真正关心哪些信息维度
- 用户关心的时间范围
- 需要多深的研究

## 不要做的事
- 不要生成 Report
- 不要选择 Tool
- 不要规划执行步骤
- 不要编造实体
- 不要输出除 JSON 以外的任何文字

## objective
只能使用以下值：

| objective | 含义 | 示例 |
|---|---|---|
| information_lookup | 用户只是了解一个对象 | "LangGraph 是什么" |
| evaluation | 评价一个项目/技术 | "LangGraph 怎么样"、"LangChain 最近社区怎么看" |
| comparison | 两个或多个对象比较 | "Qwen 和 DeepSeek 对比" |
| trend_analysis | 趋势分析 | "AI Agent 最近有什么趋势" |
| technology_research | 技术研究 | "LangGraph 原理"、"X 架构怎么实现" |
| market_research | 市场机会/市场空间 | "AI Agent 创业方向有没有机会" |
| decision_support | 用户需要建议/推荐/选型 | "推荐一个 AI Agent Framework" |
| greeting | 问候 | "hello"、"你好" |
| small_talk | 闲聊 | "谢谢"、"bye"、"今天天气怎么样" |
| help | 使用帮助 | "你能做什么"、"怎么用"、"help" |

## focus
focus 不代表任务。focus 表示用户真正关心的信息维度，允许多个。

只能从以下值中选择：
community
release
technology
ecosystem
activity
performance
architecture
adoption
sentiment
risk
opportunity
market
pricing
benchmark
documentation

示例：
- "LangChain 最近社区怎么看" → ["community", "sentiment"]
- "LangGraph 最近更新" → ["release"]
- "AI Agent 最近有什么趋势" → ["technology", "community"]
- "Qwen 和 DeepSeek 对比" → ["performance", "benchmark"]

## time_range
只能使用以下值：
- latest: 最新
- recent: 最近几个月
- historical: 历史
- future: 未来、展望、预测
- any: 不限

## depth
只能使用以下值：
- quick: 快速了解，如 "X 是什么"
- standard: 结构化分析，如 "X 怎么样"
- deep: 深度研究，如 "趋势"、"选型"、"市场机会"、"对比"

## 输出格式
只输出合法 JSON：

{
  "objective": "information_lookup",
  "entities": [],
  "focus": [],
  "time_range": "any",
  "depth": "standard",
  "raw_query": "用户原始输入"
}

## 示例

输入：
LangChain 最近社区怎么看？

输出：
{
  "objective": "evaluation",
  "entities": ["LangChain"],
  "focus": ["community", "sentiment"],
  "time_range": "recent",
  "depth": "standard",
  "raw_query": "LangChain 最近社区怎么看？"
}

输入：
最近 AI Agent Memory 有什么趋势？

输出：
{
  "objective": "trend_analysis",
  "entities": ["AI Agent Memory"],
  "focus": ["technology", "community"],
  "time_range": "recent",
  "depth": "deep",
  "raw_query": "最近 AI Agent Memory 有什么趋势？"
}

输入：
推荐一个 AI Agent Framework

输出：
{
  "objective": "decision_support",
  "entities": ["AI Agent Framework"],
  "focus": ["technology", "benchmark"],
  "time_range": "any",
  "depth": "deep",
  "raw_query": "推荐一个 AI Agent Framework"
}

输入：
hello

输出：
{
  "objective": "greeting",
  "entities": [],
  "focus": [],
  "time_range": "any",
  "depth": "quick",
  "raw_query": "hello"
}

---

现在，请对以下用户输入输出 ResearchIntent JSON，不要附加任何其他文字。
"""


class ResearchIntentRouter:
    """理解用户研究目标，输出 ResearchIntent。"""

    def __init__(self):
        self.llm = deepseek_model.with_structured_output(ResearchIntent)

    def route(self, query: str) -> ResearchIntent:
        """分析用户 query 并返回 ResearchIntent。"""
        prompt = f"""{INTENT_SYSTEM_PROMPT}

用户问题:
{query}
"""
        try:
            result = self.llm.invoke(prompt)
            if isinstance(result, ResearchIntent):
                result.raw_query = query
                return result
            if isinstance(result, dict):
                return ResearchIntent(raw_query=query, **result)
            raise ValueError(f"Unexpected LLM response type: {type(result)}")
        except Exception as exc:
            logger.warning("ResearchIntentRouter LLM error, falling back to rules: %s", exc)
            return self._rule_based_route(query)

    # ── Rule-based Fallback ────────────────────────────────────

    @staticmethod
    def _rule_based_route(query: str) -> ResearchIntent:
        """规则兜底 — LLM 调用失败时的保守路由。"""
        text = query.lower().strip()

        if ResearchIntentRouter._is_greeting(text):
            return ResearchIntent(
                objective="greeting",
                entities=[],
                focus=[],
                time_range="any",
                depth="quick",
                raw_query=query,
            )

        if ResearchIntentRouter._is_help(text):
            return ResearchIntent(
                objective="help",
                entities=[],
                focus=[],
                time_range="any",
                depth="quick",
                raw_query=query,
            )

        if ResearchIntentRouter._is_small_talk(text):
            return ResearchIntent(
                objective="small_talk",
                entities=[],
                focus=[],
                time_range="any",
                depth="quick",
                raw_query=query,
            )

        entities = ResearchIntentRouter._extract_entities(query)
        focus = ResearchIntentRouter._infer_focus(text)
        time_range = ResearchIntentRouter._infer_time_range(text)
        depth = ResearchIntentRouter._infer_depth(text)
        objective = ResearchIntentRouter._infer_objective(text)

        return ResearchIntent(
            objective=objective,
            entities=entities,
            focus=focus,
            time_range=time_range,
            depth=depth,
            raw_query=query,
        )

    @staticmethod
    def _is_greeting(text: str) -> bool:
        return text in {"hello", "hi", "hey", "你好", "您好", "早上好", "晚上好"}

    @staticmethod
    def _is_help(text: str) -> bool:
        return any(kw in text for kw in ["help", "怎么用", "使用说明", "你能做什么", "你能干什么"])

    @staticmethod
    def _is_small_talk(text: str) -> bool:
        small_talk_patterns = ["谢谢", "再见", "拜拜", "bye", "天气", "吃饭", "今天几号", "几点"]
        tech_patterns = ["github", "开源", "项目", "框架", "代码", "模型", "ai", "agent"]
        return any(kw in text for kw in small_talk_patterns) and not any(
            kw in text for kw in tech_patterns
        )

    @staticmethod
    def _infer_objective(text: str) -> str:
        if any(kw in text for kw in ["比较", "对比", "compare", "哪个好", "哪个更", "vs"]):
            return "comparison"
        if any(kw in text for kw in ["推荐", "选型", "该选", "建议", "帮我选"]):
            return "decision_support"
        if any(kw in text for kw in ["趋势", "最火", "热门", "发展", "未来", "演进"]):
            return "trend_analysis"
        if any(kw in text for kw in ["机会", "市场", "创业", "空间", "商业化"]):
            return "market_research"
        if any(kw in text for kw in ["原理", "架构", "实现", "怎么做", "如何实现", "技术细节"]):
            return "technology_research"
        if any(kw in text for kw in ["怎么样", "值得", "好不好", "评价", "社区怎么看", "风险"]):
            return "evaluation"
        return "information_lookup"

    @staticmethod
    def _infer_focus(text: str) -> list[str]:
        focus: list[str] = []
        rules: list[tuple[str, list[str]]] = [
            ("社区", ["community"]),
            ("口碑", ["sentiment"]),
            ("怎么看", ["sentiment"]),
            ("情绪", ["sentiment"]),
            ("更新", ["release"]),
            ("版本", ["release"]),
            ("release", ["release"]),
            ("技术", ["technology"]),
            ("原理", ["technology"]),
            ("架构", ["architecture"]),
            ("实现", ["architecture"]),
            ("生态", ["ecosystem"]),
            ("活跃", ["activity"]),
            ("维护", ["activity"]),
            ("性能", ["performance"]),
            ("benchmark", ["benchmark"]),
            ("基准", ["benchmark"]),
            ("采用", ["adoption"]),
            ("用户", ["adoption"]),
            ("风险", ["risk"]),
            ("机会", ["opportunity"]),
            ("市场", ["market"]),
            ("价格", ["pricing"]),
            ("pricing", ["pricing"]),
            ("文档", ["documentation"]),
        ]
        for keyword, values in rules:
            if keyword in text:
                focus.extend(values)

        if any(kw in text for kw in ["趋势", "最近"]):
            focus.extend(["technology", "community"])
        if any(kw in text for kw in ["对比", "比较", "vs"]):
            focus.extend(["performance", "benchmark"])
        if any(kw in text for kw in ["推荐", "选型"]):
            focus.extend(["technology", "benchmark"])
        if not focus:
            focus.append("technology")

        return list(dict.fromkeys(focus))

    @staticmethod
    def _infer_time_range(text: str) -> str:
        if any(kw in text for kw in ["最新", "刚刚", "最新版本", "最新更新"]):
            return "latest"
        if any(kw in text for kw in ["最近", "近期", "这几个月"]):
            return "recent"
        if any(kw in text for kw in ["历史", "过去", "演进", "发展史"]):
            return "historical"
        if any(kw in text for kw in ["未来", "将来", "展望", "预测", "下一步", "前景"]):
            return "future"
        return "any"

    @staticmethod
    def _infer_depth(text: str) -> str:
        if any(kw in text for kw in ["是什么", "介绍", "简单", "快速"]):
            return "quick"
        if any(kw in text for kw in ["趋势", "对比", "比较", "推荐", "选型", "机会", "市场", "深入"]):
            return "deep"
        return "standard"

    @staticmethod
    def _extract_entities(query: str) -> list[str]:
        """简单实体提取 — 兜底逻辑，不替代 EntityExtractor。"""
        known = [
            "LangGraph",
            "LangChain",
            "CrewAI",
            "AutoGen",
            "Dify",
            "DeepSeek",
            "Qwen",
            "Llama",
            "OpenAI",
            "Anthropic",
            "AI Agent Memory",
            "AI Agent Framework",
        ]
        lowered = query.lower()
        found = [name for name in known if name.lower() in lowered]
        if found:
            return found

        owner_repo = re.search(r"\\b[\\w.-]+/[\\w.-]+\\b", query)
        if owner_repo:
            return [owner_repo.group(0)]

        cleaned = query.strip()
        cleanup_patterns = [
            "是什么",
            "怎么样",
            "最近社区怎么看",
            "最近更新",
            "最近有什么趋势",
            "帮我研究",
            "研究一下",
            "分析",
            "推荐一个",
            "推荐",
            "对比",
            "比较",
        ]
        for pattern in cleanup_patterns:
            cleaned = cleaned.replace(pattern, " ")
        cleaned = re.sub(r"\\s+", " ", cleaned).strip(" ?？。")
        return [cleaned] if cleaned else []
