# composer.py — Research Brief Composer
#
# 职责: 将 Evidence + Signals 组合为最终 Research Brief
# 输入: user query + list[IntelligenceEvidence] + ExtractedSignals
# 输出: ResearchBrief { summary, key_findings, analysis, sources, recommendations }
#
# 与旧 AnswerComposer 的核心区别:
#   - 不输出固定 report 模板（profile/roadmap/comparison/analysis/...）
#   - 输出 ResearchBrief（结构化 JSON），而非纯文本 answer
#   - 包含 sources 追溯
#   - 带有 recommendations（行动建议）

from __future__ import annotations

import json
import logging
import re

from llms.deepseek import deepseek_structured_model
from evidence.models import IntelligenceEvidence
from research_agent.schemas.research import ResearchBrief, ExtractedSignals

logger = logging.getLogger(__name__)

COMPOSER_SYSTEM_PROMPT = """你是 AI Intelligence Research Agent 的研究简报撰写器。

## 核心职责
根据收集到的多源证据和提取的结构化信号，撰写一份结构化的 Research Brief。

## 输出格式
必须输出合法的 JSON，不超过以下字段：

{
  "summary": "一句话总结核心发现",
  "key_findings": ["发现1", "发现2", "发现3"],
  "analysis": "详细分析（自然语言，2-4段）",
  "sources": ["来源1: 说明", "来源2: 说明"],
  "recommendations": ["建议1", "建议2"]
}

## 撰写规则
1. summary: 一句话概括最重要的结论，让读者立刻知道答案
2. key_findings: 3-5 条具体发现，每条都是可独立理解的陈述
3. analysis: 详细分析，引用证据中的具体数据，说明推理过程
4. sources: 列出实际使用到的信息来源，说明每个来源提供了什么
5. recommendations: 基于分析的行动建议（如果问题不需要建议可以为空）

## 风格要求
- 输出中文
- 直接、具体、有数据支撑
- 不编造数据
- 不确定的地方明确说「不确定」
- 优先引用结构化信号中的量化评分

---

现在，请根据以下信息撰写 Research Brief，只输出 JSON。
"""


class ResearchBriefComposer:
    """将证据和信号组合为结构化研究简报。

    与旧 AnswerComposer 的区别：
    - 输出 ResearchBrief（结构化），而非 ComposedAnswer（仅 answer 字符串）
    - 不绑报告模板
    - 包含 key_findings、sources、recommendations
    """

    def __init__(self):
        self.llm = deepseek_structured_model.with_structured_output(ResearchBrief)

    def compose(
        self,
        query: str,
        evidences: list[IntelligenceEvidence],
        signals: ExtractedSignals | None = None,
    ) -> ResearchBrief:
        """撰写研究简报。

        Args:
            query: 用户原始问题
            evidences: 收集到的所有 evidence
            signals: 提取的结构化信号

        Returns:
            ResearchBrief: 结构化研究简报
        """
        # Brief Guard: 没有证据时不生成简报
        if not evidences:
            return ResearchBrief(
                summary="没有足够证据生成研究简报。",
                key_findings=["未收集到任何证据，无法进行分析。"],
                analysis="",
                signals=None,
                sources=[],
                recommendations=["请检查目标仓库是否存在，或提供其他项目名称。"],
            )

        evidence_json = self._serialize_evidences(evidences)

        signals_json = ""
        if signals is not None:
            signals_data = signals.model_dump() if hasattr(signals, "model_dump") else signals
            signals_json = f"\n\n## 结构化分析信号\n{json.dumps(signals_data, ensure_ascii=False, indent=2)}"

        prompt = f"""{COMPOSER_SYSTEM_PROMPT}

## 用户问题
{query}

## 证据数据
{evidence_json}
{signals_json}
"""
        try:
            result = self.llm.invoke(prompt)
            if isinstance(result, ResearchBrief):
                return result
            if isinstance(result, dict):
                return ResearchBrief(**result)
            raise ValueError(f"Unexpected LLM response type: {type(result)}")
        except Exception as exc:
            logger.warning("ResearchBriefComposer LLM error: %s", exc)
            return self._fallback_brief(query, evidences, signals, str(exc))

    def compose_fast(
        self,
        query: str,
        evidences: list[IntelligenceEvidence],
        signals: ExtractedSignals | None = None,
    ) -> ResearchBrief:
        """快速生成简报：不调用 LLM，直接基于 evidence 拼出可用答案。"""
        return self._fallback_brief(query, evidences, signals, "")

    # ── Serialization ──────────────────────────────────────────

    @staticmethod
    def _serialize_evidences(evidences: list[IntelligenceEvidence]) -> str:
        serialized = []
        for i, ev in enumerate(evidences):
            if ev is None:
                continue
            try:
                if hasattr(ev, 'model_dump'):
                    data = ev.model_dump()
                elif hasattr(ev, 'dict'):
                    data = ev.dict()
                else:
                    data = str(ev)
                serialized.append({"step": i, "data": data})
            except Exception:
                serialized.append({"step": i, "data": str(ev)})
        return json.dumps(serialized, ensure_ascii=False, indent=2)

    @staticmethod
    def _fallback_brief(
        query: str,
        evidences: list[IntelligenceEvidence],
        signals: ExtractedSignals | None,
        reason: str,
    ) -> ResearchBrief:
        """LLM compose 失败时，用已有 evidence/signals 生成可用简报。"""
        key_findings: list[str] = []
        sources: list[str] = []
        recommendations: list[str] = []
        analysis_parts: list[str] = []

        for evidence in evidences:
            github = evidence.github if evidence else None
            repo = github.repository if github else None
            if repo:
                repo_name = repo.full_name or "该仓库"
                key_findings.append(
                    f"{repo_name} 是一个以 {repo.language or '未知语言'} 为主的 GitHub 项目，"
                    f"当前约有 {repo.stars} stars、{repo.forks} forks。"
                )
                if repo.description:
                    key_findings.append(f"项目描述：{repo.description}")
                sources.append(f"GitHub repository: {repo_name}")

            if github and github.readme:
                readme_preview = _clean_snippet(github.readme, 300)
                if readme_preview:
                    analysis_parts.append(f"README 摘要片段：{readme_preview}...")
                    sources.append("GitHub README")

            if github and github.commit_activity:
                key_findings.append(
                    f"近期维护活跃度：近 30 天约 {github.commit_activity.commits_last_30_days} 次提交，"
                    f"近 90 天约 {github.commit_activity.commits_last_90_days} 次提交。"
                )
                sources.append("GitHub commit activity")

            reddit = evidence.reddit if evidence else None
            if reddit and reddit.posts:
                reddit_summaries = [_reddit_summary(post) for post in reddit.posts[:3]]
                reddit_summaries = [item for item in reddit_summaries if item]
                if reddit_summaries:
                    key_findings.append(f"Reddit 相关讨论：{reddit_summaries[0]}")
                else:
                    key_findings.append(
                        f"社区讨论方面，当前抓取到 {reddit.mentions or len(reddit.posts)} 条 Reddit 相关讨论。"
                    )
                for post in reddit.posts[:3]:
                    preview = _reddit_summary(post) or _clean_snippet(post, 300)
                    if preview:
                        analysis_parts.append(f"Reddit 讨论片段：{preview}...")
                sources.append("Reddit community discussions")

            web = evidence.web if evidence else None
            if web and web.pages:
                key_findings.append(f"Web 资料方面，当前读取到 {len(web.pages)} 个公开页面。")
                for page in web.pages[:2]:
                    url = _clean_url(page.get("url") or "")
                    content = _clean_web_snippet(page.get("content") or page.get("summary") or "", 400)
                    if content:
                        source_label = f"（{url}）" if url else ""
                        analysis_parts.append(f"Web 页面片段{source_label}：{content}...")
                    if url:
                        sources.append(f"Web page: {url}")

        if signals:
            if signals.technology and signals.technology.summary:
                key_findings.append(signals.technology.summary)
            if signals.community and signals.community.summary:
                key_findings.append(signals.community.summary)
            if signals.ecosystem and signals.ecosystem.summary:
                key_findings.append(signals.ecosystem.summary)

        if not key_findings:
            key_findings.append("当前没有收集到足够证据，无法给出可靠结论。")
            recommendations.append("检查实体解析结果是否正确，或补充明确的 GitHub 仓库、官网、文档链接。")

        if reason:
            analysis_parts.append(f"结构化撰写模型未返回有效结果，已使用 fallback 简报。内部原因：{reason}")

        summary = f"关于「{query[:50]}」的研究已基于现有证据生成快速简报。"
        if key_findings:
            summary = key_findings[0]

        return ResearchBrief(
            summary=summary,
            key_findings=key_findings[:6],
            analysis="\n\n".join(analysis_parts),
            signals=signals,
            sources=list(dict.fromkeys(sources)),
            recommendations=recommendations,
        )


def _clean_url(value: str) -> str:
    """清理 URL 外层 Markdown 符号。"""
    return str(value or "").strip().strip("`").strip()


def _clean_snippet(value: str, limit: int) -> str:
    """清理网页/社区正文片段，避免图片、导航和 blob 链接污染 fast brief。"""
    text = str(value or "")
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[[^\]]*\]\((?:javascript:|blob:)[^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`?https?://[^\s`<>)]+`?", " ", text)
    text = re.sub(r"blob:http://[^\s)]+", " ", text)
    text = re.sub(r"javascript:;", " ", text)
    text = re.sub(r"[`*_#>]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].strip()


def _clean_web_snippet(value: str, limit: int) -> str:
    """清理 Jina Markdown 的网页片段，只保留正文性内容。"""
    text = str(value or "")
    text = re.sub(r"^Title:\s*", "", text, flags=re.I)
    text = re.sub(r"\bURL Source:\s*.*?(?=(Published Time:|Markdown Content:|$))", " ", text, flags=re.I | re.S)
    text = re.sub(r"\bPublished Time:\s*.*?(?=(Markdown Content:|$))", " ", text, flags=re.I | re.S)
    text = re.sub(r"\bMarkdown Content:\s*", " ", text, flags=re.I)
    text = re.sub(r"\[[^\]]{1,20}\]\(\s*\)", " ", text)
    text = re.sub(r"(?:\s*/\s*){2,}", " ", text)
    return _clean_snippet(text, limit)


def _reddit_summary(value: str) -> str:
    """从 opencli Reddit YAML 文本中提取可读摘要。"""
    text = str(value or "")
    blocks = re.split(r"\n(?=- id: )", text.strip())
    summaries: list[str] = []
    for block in blocks[:3]:
        title = _yaml_value(block, "title")
        subreddit = _yaml_value(block, "subreddit")
        comments = _yaml_value(block, "comments")
        score = _yaml_value(block, "score")
        if not title:
            continue
        meta = []
        if subreddit:
            meta.append(subreddit)
        if score:
            meta.append(f"{score} 分")
        if comments:
            meta.append(f"{comments} 评论")
        suffix = f"（{'，'.join(meta)}）" if meta else ""
        summaries.append(f"{title}{suffix}")
    return "；".join(summaries)


def _yaml_value(block: str, key: str) -> str:
    match = re.search(rf"^\s*{re.escape(key)}:\s*(.*)$", block, re.MULTILINE)
    return match.group(1).strip(" '\"") if match else ""
