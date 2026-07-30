# 9 个 Capability 工具（GitHub 4 个 + HF 1 个 + 社区/Web/视频 4 个）

import json
from typing import Any

from langchain_core.tools import tool

from agent.tools._shared import github, huggingface, with_policy_logging, record, capability_result
from agent.tools._raw import (
    read_reddit_post_raw,
    read_webpage_raw,
    read_bilibili_video_raw,
    youtube_transcript_raw,
    read_rss_raw,
    transcribe_podcast_raw,
)


# ── Capability 工具 ─────────────────────────────────────────

@tool
@with_policy_logging("github_project_profile")
def github_project_profile(owner: str, repo: str) -> dict[str, Any]:
    """
    获取 GitHub 项目的基础画像证据。

    自动聚合 repository + README，返回统一 Capability Evidence。
    当需要了解项目定位、用途、技术栈、基础元数据时使用。
    """
    repository = github.get_repository(owner, repo)
    readme_content = github.get_readme(owner, repo)
    summary = (
        f"{repository.get('full_name', f'{owner}/{repo}')} 是一个"
        f"以 {repository.get('language') or '未知语言'} 为主的项目，"
        f"当前 stars={repository.get('stars', repository.get('stargazers_count', 0))}。"
    )
    result = capability_result(
        source="github",
        evidence_type="project_profile",
        summary=summary,
        evidence={
            "repository": repository,
            "readme": readme_content,
        },
    )
    return record("github_project_profile", {"owner": owner, "repo": repo}, result)


@tool
@with_policy_logging("github_project_health")
def github_project_health(owner: str, repo: str) -> dict[str, Any]:
    """
    获取 GitHub 项目的健康度证据。

    自动聚合 issues + pull_requests + commit_activity。
    当需要判断维护活跃度、问题响应和开发节奏时使用。
    """
    issue_items = github.get_issues(owner, repo)
    pr_items = github.get_pull_requests(owner, repo)
    commit_activity = github.get_commit_activity(owner, repo)
    summary = (
        f"{owner}/{repo} 近 30 天提交数="
        f"{commit_activity.get('commits_last_30_days', 0)}，"
        f"近 90 天提交数={commit_activity.get('commits_last_90_days', 0)}。"
    )
    result = capability_result(
        source="github",
        evidence_type="project_health",
        summary=summary,
        evidence={
            "issues": issue_items,
            "pull_requests": pr_items,
            "commit_activity": commit_activity,
        },
    )
    return record("github_project_health", {"owner": owner, "repo": repo}, result)


@tool
@with_policy_logging("github_release_summary")
def github_release_summary(owner: str, repo: str) -> dict[str, Any]:
    """
    获取 GitHub 项目的发布与规划证据。

    自动聚合 releases + planning_signals。
    当需要了解版本变化、近期发布、路线图和里程碑时使用。
    """
    release_items = github.get_releases(owner, repo)
    planning = github.get_planning_signals(owner, repo)
    release_count = len(release_items or [])
    milestone_count = len(planning.get("milestones", []) or [])
    summary = f"{owner}/{repo} 获取到 {release_count} 条 release 和 {milestone_count} 个开放里程碑。"
    result = capability_result(
        source="github",
        evidence_type="release_summary",
        summary=summary,
        evidence={
            "releases": release_items,
            "planning": planning,
        },
    )
    return record("github_release_summary", {"owner": owner, "repo": repo}, result)


@tool
@with_policy_logging("github_ecosystem")
def github_ecosystem(owner: str, repo: str) -> dict[str, Any]:
    """
    获取 GitHub 项目的社区生态证据。

    自动聚合 discussion + planning。
    当需要了解社区讨论、维护者参与、生态动向和未来信号时使用。
    """
    discussions = github.get_discussion_signals(owner, repo)
    planning = github.get_planning_signals(owner, repo)
    topic_count = len(discussions.get("hot_topics", []) or [])
    enhancement_count = len(planning.get("enhancement_issues", []) or [])
    summary = f"{owner}/{repo} 获取到 {topic_count} 个讨论热点和 {enhancement_count} 条增强/提案信号。"
    result = capability_result(
        source="github",
        evidence_type="community_evidence",
        summary=summary,
        evidence={
            "discussions": discussions,
            "planning": planning,
        },
    )
    return record("github_ecosystem", {"owner": owner, "repo": repo}, result)


@tool
@with_policy_logging("huggingface_model_profile")
def huggingface_model_profile(model_id: str) -> dict[str, Any]:
    """
    获取 HuggingFace 模型画像证据。

    当 github_search 不能覆盖模型资源，且已发现 HuggingFace model_id 时使用。
    """
    model = huggingface.get_model(model_id)
    summary = (
        f"{model_id} 下载量={model.get('downloads', 0)}，"
        f"likes={model.get('likes', 0)}，任务类型={model.get('pipeline_tag')}。"
    )
    result = capability_result(
        source="huggingface",
        evidence_type="model_profile",
        summary=summary,
        evidence={"model": model},
    )
    return record("huggingface_model_profile", {"model_id": model_id}, result)


@tool
@with_policy_logging("community_reader")
def community_reader(identifier: str, platform: str = "community") -> dict[str, Any]:
    """读取社区资源内容，支持 twitter / reddit / bilibili / v2ex。"""
    content: Any
    evidence_type = "community_discussion"

    if identifier.startswith("twitter:"):
        # Twitter 没有"读特定推文"的能力，搜索结果已在 community_search 中返回
        # 直接从 discovery 的 reason 字段获取，无需重复搜索
        content = "Twitter 搜索结果已在 community_search 阶段返回，请使用 discovery 结果中的内容。"
        platform = "twitter"
        summary = f"Twitter 无需单独读取: {identifier}"
    elif identifier.startswith("reddit:"):
        post_id = identifier.removeprefix("reddit:")
        platform = "reddit"
        content = read_reddit_post_raw(post_id, limit=10)
        summary = f"读取 Reddit 帖子: {post_id}"
    elif identifier.startswith("bilibili:"):
        value = identifier.removeprefix("bilibili:")
        platform = "bilibili"
        # 从 identifier 提取 bvid，走 B站 API 而非 Jina Reader
        bvid = value.replace("https://www.bilibili.com/video/", "")
        content = read_bilibili_video_raw(bvid)
        summary = f"读取 B站视频信息及评论: {bvid}"
    elif identifier.startswith("v2ex:"):
        value = identifier.removeprefix("v2ex:")
        platform = "v2ex"
        content = read_webpage_raw(value) if value.startswith("http") else "V2EX 搜索已停用"
        summary = f"读取 V2EX 资源: {value}"
    else:
        content = f"暂不支持的社区资源 identifier: {identifier}"
        summary = "社区资源读取未匹配到具体平台"

    result = capability_result(
        source="community",
        evidence_type=evidence_type,
        summary=summary,
        evidence={
            "identifier": identifier,
            "platform": platform,
            "content": content,
        },
    )
    return record("community_reader", {"identifier": identifier, "platform": platform}, result)


@tool
@with_policy_logging("webpage_reader")
def webpage_reader(url: str) -> dict[str, Any]:
    """读取网页正文。并文本清理噪声"""
    url = url.strip().strip("`")
    content = read_webpage_raw(url)
    result = capability_result(
        source="web",
        evidence_type="webpage",
        summary=f"读取网页正文: {url}",
        evidence={"url": url, "content": content},
    )
    return record("webpage_reader", {"url": url}, result)


@tool
@with_policy_logging("youtube_transcript")
def youtube_transcript(video_url: str) -> dict[str, Any]:
    """读取 YouTube 视频字幕或元信息。"""
    transcript = youtube_transcript_raw(video_url)
    result = capability_result(
        source="youtube",
        evidence_type="youtube_transcript",
        summary=f"读取 YouTube 字幕/转写: {video_url}",
        evidence={"video_url": video_url, "transcript": transcript},
    )
    return record("youtube_transcript", {"video_url": video_url}, result)


@tool
@with_policy_logging("rss_reader")
def rss_reader(url: str) -> dict[str, Any]:
    """读取 RSS/Atom 订阅源。"""
    content = read_rss_raw(url)
    result = capability_result(
        source="web",
        evidence_type="rss_feed",
        summary=f"读取 RSS/Atom: {url}",
        evidence={"url": url, "items": content},
    )
    return record("rss_reader", {"url": url}, result)


@tool
@with_policy_logging("podcast_transcript")
def podcast_transcript(url: str) -> dict[str, Any]:
    """转录小宇宙播客。"""
    transcript = transcribe_podcast_raw(url)
    result = capability_result(
        source="youtube",
        evidence_type="podcast_transcript",
        summary=f"转录小宇宙播客: {url}",
        evidence={"url": url, "transcript": transcript},
    )
    return record("podcast_transcript", {"url": url}, result)
