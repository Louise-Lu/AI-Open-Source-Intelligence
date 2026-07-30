# intent.py — 理解用户意图
#
# 输入: 用户原始 query
# 输出: ResearchIntent { objective, entities, focus, depth, raw_query }
#       + 正则提取: time_range, platform_hint
#
# 注意：IntentRouter 不是任务分类器，不生成报告，不选择工具，不规划步骤。

from __future__ import annotations

import logging
import re

from llms.deepseek import deepseek_structured_model
from research_agent.schemas.research import ResearchIntent

logger = logging.getLogger(__name__)


# ── 正则提取（不经过 LLM） ──────────────────────────────────


def extract_time_range(query: str) -> str:
    """从 raw_query 中提取时间范围关键词。

    全部基于 .lower() 后的文本匹配，大小写不敏感。
    """
    text = query.lower()
    if any(kw in text for kw in ["最新", "刚刚", "最新版本", "最新更新", "latest"]):
        return "latest"
    if any(kw in text for kw in [
        "最近", "近期", "这几个月", "前段时间", "前几周", "上个月", "前一阵",
        "过去一周", "过去一个月", "过去几个月",
        "recent", "recently", "lately",
    ]):
        return "recent"
    if any(kw in text for kw in [
        "历史", "演进", "发展史", "发展历程", "发展历史",
        "historical", "history",
    ]):
        return "historical"
    if any(kw in text for kw in [
        "未来", "将来", "展望", "预测", "下一步", "前景", "future", "upcoming",
    ]):
        return "future"
    # 年份匹配：2025/2026 → recent
    if re.search(r"20[2-9]\d", text):
        return "recent"
    return "any"


def extract_platforms(query: str) -> list[str]:
    """从 raw_query 中提取用户显式提到的社区平台。

    全部基于 .lower() 后的文本匹配，大小写不敏感。
    """
    text = query.lower()
    platforms: list[str] = []
    if any(kw in text for kw in ["reddit"]):
        platforms.append("reddit")
    if any(kw in text for kw in ["twitter", "x上", "x 上", "推特"]):
        platforms.append("twitter")
    if any(kw in text for kw in ["小红书", "xhs", "红书"]):
        platforms.append("xhs")
    if any(kw in text for kw in ["b站", "bilibili", "b 站"]):
        platforms.append("bilibili")
    if any(kw in text for kw in ["v2ex"]):
        platforms.append("v2ex")
    if any(kw in text for kw in ["youtube", "yt", "youtube上"]):
        platforms.append("youtube")
    return platforms


INTENT_SYSTEM_PROMPT = """你是 AI Intelligence Research Agent 的研究目标理解器。

## 核心职责
理解用户真正的研究目标，输出结构化的 ResearchIntent JSON。

你的职责不是决定执行哪个 Pipeline，也不是规划步骤，而是理解：
- 用户想了解什么对象
- 用户真正关心哪些信息维度
- 需要多深的研究

注意：时间范围和平台偏好由系统自动从原始查询中提取，你不需要处理。

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
| evaluation | 评价一个项目/技术 | "LangGraph 怎么样"、"LangChain 社区怎么看" |
| comparison | 两个或多个对象比较 | "Qwen 和 DeepSeek 对比" |
| trend_analysis | 趋势分析 | "AI Agent 有什么趋势" |
| technology_research | 技术研究 | "LangGraph 原理"、"X 架构怎么实现" |
| market_research | 市场机会/市场空间 | "AI Agent 创业方向有没有机会" |
| decision_support | 用户需要建议/推荐/选型 | "推荐一个 AI Agent Framework" |
| greeting | 问候 | "hello"、"你好" |
| small_talk | 闲聊 | "谢谢"、"bye"、"今天天气怎么样" |
| help | 使用帮助 | "你能做什么"、"怎么用"、"help" |

## focus
focus 不代表任务。focus 表示用户真正关心的信息研究维度，允许多个。

只能从以下值中选择：
community
developer
official
technology
ecosystem
adoption
sentiment
trend
benchmark
market
opportunity
risk
recent_updates

**核心原则**：focus 应该反映用户真正关心的信息维度，不要过度解读或机械匹配关键词。

示例：
- "OpenAI 发布了什么？" → ["official","recent_updates"]
- "LangGraph 多少星？" → ["developer"]（只是查询 GitHub 数据）
- "LangChain 有多少人用？" → ["adoption"]（关注采用情况）
- "AI Agent 有什么趋势？" → ["trend","market","technology","community","adoption"]
- "推荐 Agent Framework" → ["benchmark","ecosystem","adoption","risk"]
- "LangGraph 和 CrewAI 哪个好？" → ["benchmark","community","technology"]

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
  "depth": "standard",
  "raw_query": "用户原始输入"
}

## 示例

输入：
LangGraph 多少星？

输出：
{
  "objective": "information_lookup",
  "entities": ["LangGraph"],
  "focus": ["developer"],
  "depth": "quick",
  "raw_query": "LangGraph 多少星？"
}

输入：
LangChain 是什么？

输出：
{
  "objective": "information_lookup",
  "entities": ["LangChain"],
  "focus": ["official", "developer"],
  "depth": "quick",
  "raw_query": "LangChain 是什么？"
}

输入：
LangChain 有多少人用？

输出：
{
  "objective": "information_lookup",
  "entities": ["LangChain"],
  "focus": ["adoption"],
  "depth": "quick",
  "raw_query": "LangChain 有多少人用？"
}

输入：
LangChain 社区怎么看？

输出：
{
  "objective": "evaluation",
  "entities": ["LangChain"],
  "focus": ["community", "sentiment"],
  "depth": "standard",
  "raw_query": "LangChain 社区怎么看？"
}

输入：
AI Agent Memory 有什么趋势？

输出：
{
  "objective": "trend_analysis",
  "entities": ["AI Agent Memory"],
  "focus": ["trend", "market", "technology", "community", "adoption"],
  "depth": "deep",
  "raw_query": "AI Agent Memory 有什么趋势？"
}

输入：
推荐一个 AI Agent Framework

输出：
{
  "objective": "decision_support",
  "entities": ["AI Agent Framework"],
  "focus": ["technology", "benchmark", "ecosystem", "adoption", "risk"],
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
  "depth": "quick",
  "raw_query": "hello"
}

---

现在，请对以下用户输入输出 ResearchIntent JSON，不要附加任何其他文字。
"""


class ResearchIntentRouter:
    """理解用户研究目标，输出 ResearchIntent。"""

    def __init__(self):
        self.llm = deepseek_structured_model.with_structured_output(ResearchIntent)

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
                depth="quick",
                raw_query=query,
            )

        if ResearchIntentRouter._is_help(text):
            return ResearchIntent(
                objective="help",
                entities=[],
                focus=[],
                depth="quick",
                raw_query=query,
            )

        if ResearchIntentRouter._is_small_talk(text):
            return ResearchIntent(
                objective="small_talk",
                entities=[],
                focus=[],
                depth="quick",
                raw_query=query,
            )

        entities = ResearchIntentRouter._extract_entities(query)
        focus = ResearchIntentRouter._infer_focus(text)
        depth = ResearchIntentRouter._infer_depth(text)
        objective = ResearchIntentRouter._infer_objective(text)

        return ResearchIntent(
            objective=objective,
            entities=entities,
            focus=focus,
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
            ("开发者", ["developer"]),
            ("口碑", ["sentiment"]),
            ("怎么看", ["sentiment"]),
            ("情绪", ["sentiment"]),
            ("更新", ["official", "recent_updates"]),
            ("版本", ["official", "recent_updates"]),
            ("release", ["official", "recent_updates"]),
            ("官方", ["official"]),
            ("技术", ["technology"]),
            ("原理", ["technology"]),
            ("架构", ["technology"]),
            ("实现", ["technology"]),
            ("生态", ["ecosystem"]),
            ("采用", ["adoption"]),
            ("用户", ["adoption"]),
            ("趋势", ["trend"]),
            ("风险", ["risk"]),
            ("机会", ["opportunity"]),
            ("市场", ["market"]),
            ("benchmark", ["benchmark"]),
            ("基准", ["benchmark"]),
        ]
        for keyword, values in rules:
            if keyword in text:
                focus.extend(values)

        if any(kw in text for kw in ["趋势", "最近"]):
            focus.extend(["trend", "community"])
        if any(kw in text for kw in ["对比", "比较", "vs"]):
            focus.extend(["benchmark", "technology"])
        if any(kw in text for kw in ["推荐", "选型"]):
            focus.extend(["technology", "benchmark", "risk"])
        if not focus:
            focus.append("technology")

        return list(dict.fromkeys(focus))

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
