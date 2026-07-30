# 5 个 Discovery 工具（github/huggingface/community/youtube/web）

import re
from typing import Any

from langchain_core.tools import tool

from agent.schemas.discovery_result import discovery_result
from agent.tools._shared import with_policy_logging, record, truncate_text
from agent.tools._raw import (
    search_github_raw,
    search_huggingface_raw,
    search_twitter_raw,
    search_reddit_raw,
    parse_reddit_posts,
    search_bilibili_raw,
    search_youtube_raw,
    search_web_raw,
)


# ── Discovery 工具 ─────────────────────────────────────────

@tool
@with_policy_logging("github_search")
def github_search(query: str) -> list[dict[str, Any]]:
    """
    搜索 GitHub 仓库，用于 Research Agent 自主发现候选数据源。

    Args:
        query: 实体名称、技术方向或关键词，例如 "LangGraph"、"AI Agent"。

    返回：最多 2 个最相关的 DiscoveryResult，identifier 为 owner/repo。
    重要：当你需要 GitHub 证据但还不知道 owner/repo 时，必须先调用此工具。
    """
    tool_input = {"query": query}
    items = _rank_github_search_items(query, search_github_raw(query))
    result = [
        discovery_result(
            source="github",
            identifier=item.get("full_name", ""),
            title=item.get("full_name", ""),
            url=item.get("html_url", ""),
            score=float(item.get("stargazers_count", 0) or 0),
            reason=item.get("description") or "GitHub 仓库搜索结果",
        )
        for item in items[:2]
        if item.get("full_name")
    ]
    return record("github_search", tool_input, result)

def _rank_github_search_items(query: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """GitHub Search 默认按 stars 排序，容易把父项目排前；这里按 repo 名称相关性重排。"""
    normalized_query = _normalize_repo_token(query)
    seen: set[str] = set()
    unique_items = []
    for item in items:
        full_name = str(item.get("full_name") or "")
        if not full_name or full_name in seen:
            continue
        seen.add(full_name)
        unique_items.append(item)

    def rank_key(item: dict[str, Any]) -> tuple[int, int, float]:
        full_name = str(item.get("full_name") or "").lower()
        repo_name = full_name.split("/")[-1]
        normalized_repo = _normalize_repo_token(repo_name)
        stars = float(item.get("stargazers_count", 0) or 0)

        if normalized_repo == normalized_query:
            match_rank = 0
        elif normalized_query and normalized_query in normalized_repo:
            match_rank = 1
        elif normalized_query and normalized_query in _normalize_repo_token(full_name):
            match_rank = 2
        else:
            match_rank = 3

        return (match_rank, -len(normalized_repo), -stars)

    return sorted(unique_items, key=rank_key)

def _normalize_repo_token(value: str) -> str:
    """把 repo 名称和 query 归一化，便于 langgraph / LangGraph 这类匹配。"""
    text = value.lower()
    text = re.sub(r"https?://github\.com/", " ", text)
    text = re.sub(r"\brepo:", " ", text)
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


@tool
@with_policy_logging("huggingface_search")
def huggingface_search(query: str) -> list[dict]:
    """
    搜索 HuggingFace 模型，用于 Research Agent 自主发现模型/数据集/空间资源。

    Args:
        query: 实体名称、模型名称或技术关键词。

    返回：候选模型 DiscoveryResult，identifier 为 model_id。
    """
    tool_input = {"query": query}
    items = search_huggingface_raw(query)
    result = [
        discovery_result(
            source="huggingface",
            identifier=item.get("id", ""),
            title=item.get("id", ""),
            url=f"https://huggingface.co/{item.get('id')}",
            score=float(item.get("downloads", 0) or 0),
            reason=f"任务类型: {item.get('pipeline_tag') or 'unknown'}",
        )
        for item in items or []
        if item.get("id")
    ]
    return record("huggingface_search", tool_input, result)


@tool
@with_policy_logging("community_search")
def community_search(query: str, platforms: list[str] | None = None) -> list[dict[str, Any]]:
    """
    搜索社区讨论资源。

    Args:
        query: 搜索关键词（Reddit 不支持中文，建议用英文）。
        platforms: 社区平台列表，例如 ["twitter", "reddit", "bilibili", "v2ex"]。

    返回：社区资源 DiscoveryResult，identifier 带平台前缀。
    """
    platforms = platforms or ["reddit"]
    tool_input = {"query": query, "platforms": platforms}

    result: list[dict[str, Any]] = []

    if "twitter" in platforms or "x" in platforms:
        twitter_output = search_twitter_raw(query, limit=5)
        if twitter_output.strip() and not _is_failed_search_output(twitter_output):
            result.append(
                discovery_result(
                    source="community",
                    identifier=f"twitter:{query}",
                    title=f"Twitter/X: {query}",
                    url="",
                    score=0.0,
                    reason=truncate_text(twitter_output, 2000),
                )
            )
        else:
            # Twitter 不可用时明确告知 Agent，避免重复调用
            result.append(
                discovery_result(
                    source="community",
                    identifier=f"twitter:unavailable",
                    title="Twitter/X 不可用",
                    url="",
                    score=0.0,
                    reason="Twitter/X API 当前不可用（凭据过期或服务异常），请勿重试 community_search 获取 Twitter 数据。可改用 web_search 搜索 Twitter 相关内容。",
                )
            )

    if "reddit" in platforms:
        reddit_output = search_reddit_raw(query, limit=5)
        if reddit_output.strip() and not _is_failed_search_output(reddit_output):
            # 解析成独立帖子，每条帖子一个 DiscoveryResult
            posts = parse_reddit_posts(reddit_output)
            for post in posts[:5]:
                post_id = post.get("id", "")
                if not post_id:
                    continue
                result.append(
                    discovery_result(
                        source="community",
                        identifier=f"reddit:{post_id}",
                        title=post.get("title", f"Reddit 帖子 {post_id}"),
                        url=post.get("url", ""),
                        score=float(post.get("score", 0) or 0),
                        reason=truncate_text(post.get("selftext", ""), 500),
                    )
                )

    if "bilibili" in platforms or "b站" in platforms:
        for item in search_bilibili_raw(query, limit=3):
            if item.get("error"):
                continue
            identifier = item.get("bvid") or f"bilibili:{query}"
            result.append(
                discovery_result(
                    source="community",
                    identifier=f"bilibili:{identifier}",
                    title=item.get("title", "B站搜索结果"),
                    url=item.get("url", ""),
                    score=float(item.get("play", 0) or 0),
                    reason=f"B站视频搜索结果，UP主：{item.get('up', 'unknown')}",
                )
            )

    # V2EX 已停用（搜索 API 不可用，热门列表过滤命中率极低）

    return record("community_search", tool_input, result) if result else record(
        "community_search",
        tool_input,
        {
            "source": "community",
            "type": "empty_result",
            "summary": f"社区搜索未找到结果。query={query}, platforms={platforms}",
            "suggestion": "请尝试更简短的关键词，例如只用实体名 'CrewAI'，去掉 sentiment/year 等修饰词。",
        },
    )

def _is_failed_search_output(output: str) -> bool:
    """判断社区搜索是否是失败信息，失败信息不能作为有效 DiscoveryResult。"""
    text = output.strip().lower()
    return (
        not text
        or text.startswith("搜索失败")
        or text.startswith("获取失败")
        or '"ok": false' in text
        or "timeout" in text
        or "tool-not-found" in text
    )


@tool
@with_policy_logging("youtube_search")
def youtube_search(query: str) -> list[dict[str, Any]]:
    """搜索 YouTube 视频资源。"""
    tool_input = {"query": query}
    result = [
        discovery_result(
            source="youtube",
            identifier=item.get("url", ""),
            title=item.get("title", "YouTube 搜索结果"),
            url=item.get("url", ""),
            score=float(item.get("duration", 0) or 0),
            reason=f"YouTube 视频，上传者：{item.get('uploader', 'unknown')}",
        )
        for item in search_youtube_raw(query, limit=5)
        if item.get("url")
    ]
    return record("youtube_search", tool_input, result)


@tool
@with_policy_logging("web_search")
def web_search(query: str) -> list[dict[str, Any]]:
    """搜索公开 Web 资料。"""
    tool_input = {"query": query}
    urls = search_web_raw(query)

    if not urls:
        return record("web_search", tool_input, [])

    result = [
        discovery_result(
            source="web",
            identifier=url,
            title=f"Web 搜索结果: {url}",
            url=url,
            score=0.0,
            reason=f"Web 搜索: {query}",
        )
        for url in urls
    ]
    return record("web_search", tool_input, result)
