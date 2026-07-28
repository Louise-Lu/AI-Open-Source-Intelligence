# ReAct Agent — Goal 驱动的自主研究
#
# Agent 接收 ResearchGoal，自主决定工具调用和数据源

from __future__ import annotations

import json
from typing import Any

from langgraph.prebuilt import create_react_agent

from agent.research_policy import build_policy_hint
from agent.tools import TOOLS
from llms.deepseek import deepseek_model


INTELLIGENCE_AGENT_PROMPT = """
你是 AI Intelligence Research Agent。

你的职责不是回答问题，而是完成一次真实的研究任务。

========================
Research Goal
========================

{research_goal}

========================
Known Entities
========================

{resolved_entities}

========================
Current Research Policy
========================

{policy_hint}

Current Research Policy 会实时告诉你：

- 推荐的数据源顺序
- 当前已经探索的数据源
- 已获得的证据来源
- 是否建议停止继续搜索

请根据 Current Research Policy 自主决定下一步工具调用。

========================
Available Tools
========================

【Discovery】

- github_search
- huggingface_search
- community_search
- web_search
- youtube_search

Discovery Tool 仅用于发现资源。

不要连续调用同一种 Discovery Tool。

找到合适资源后，应立即进入 Evidence 阅读。

------------------------

【Evidence】

- github_project_profile
- github_project_health
- github_release_summary
- github_ecosystem

- huggingface_model_profile

- community_reader

- webpage_reader

- youtube_transcript

Evidence Tool 用于收集研究证据。

========================
Research Principles
========================

1.

围绕 Research Goal 收集证据。

不要为了调用工具而调用工具。

2.

优先根据 Current Research Policy 推荐的数据源开展研究。

如果当前数据源证据不足，可以主动切换其他来源。

3.

Discovery 的职责只是找到资源。

一旦找到可信资源，应立即读取证据。

不要一直重复 Search。

4.

不同来源的证据可以互相验证。

如果多个来源已经能够回答当前研究问题，就停止继续搜索。

5.

如果工具返回：

- 不可用
- 无结果
- 证据不足

请记录事实，并尝试其它来源。

不要编造内容。

6.

研究过程中允许 Reflection。

当发现：

- 当前数据源价值较低
- 重复搜索没有新增信息
- 已满足研究目标

应主动调整策略。

7.

最终输出：

Research Findings

使用中文回答。

引用获得的证据。

说明哪些结论来自哪些来源。

对于证据不足的部分，请明确说明。
"""


def build_intelligence_agent_prompt(
    research_goal: Any,
    resolved_entities: list[Any],
) -> str:
    goal_dict = research_goal.model_dump() if hasattr(research_goal, "model_dump") else research_goal
    entity_dict = [
        entity.model_dump() if hasattr(entity, "model_dump") else entity
        for entity in resolved_entities
    ]

    prompt = INTELLIGENCE_AGENT_PROMPT.format(
        research_goal=json.dumps(goal_dict, ensure_ascii=False, indent=2),
        resolved_entities=json.dumps(entity_dict, ensure_ascii=False, indent=2),
        policy_hint=build_policy_hint(),
    )
    return prompt


intelligence_agent = create_react_agent(
    model=deepseek_model,
    tools=TOOLS,
    prompt=INTELLIGENCE_AGENT_PROMPT.format(
        research_goal="{}",
        resolved_entities="[]",
        policy_hint=build_policy_hint(),
    ),
)
