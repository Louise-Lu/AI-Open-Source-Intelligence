from functools import wraps
from typing import Any

from langchain_core.tools import tool

from agent.research_policy import after_tool_call, before_tool_call, build_policy_hint
from agent.trace import add_trace
from agent.schemas.discovery_result import discovery_result
from sources.github.client import GitHubAPI
from sources.huggingface.client import HuggingFaceClient

github = GitHubAPI()
huggingface = HuggingFaceClient()

## 进入 tool 前，打印 当前的 policy_state
## 调用 tool 后，打印 当前的 policy_state
def _print_policy_hint(label: str, tool_name: str) -> None:
    print(f"\n========== POLICY {label}: {tool_name} ==========")
    print(build_policy_hint())

# 给所有 tool 加 decorator，进入 tool 前会先打印
def _with_policy_logging(tool_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _print_policy_hint("BEFORE", tool_name)
            return func(*args, **kwargs)

        return wrapper

    return decorator


# tool 调用之后，_record 
    # 1. 更新 policy_state 和 Trace
    # 2. 把 tool_output + policy_hint 给 LLM 的 Observation
def _record(tool_name: str, tool_input: dict, tool_output, *, update_policy: bool = True):

    if update_policy:
        # 更新 policy_state 
        after_tool_call(tool_name, tool_output)

    # 更新 trace 
    add_trace(tool_name, tool_input, tool_output)

    _print_policy_hint("AFTER", tool_name)

    # 给 LLM 的 Observation：
    # result 是工具原始结果，policy_hint 是更新后的 最新研究策略。
    # 这样下一轮 thought 能看到最新进度，而不只是终端里能看到 print。
    return {
        "result": tool_output,
        "policy_hint": build_policy_hint(),
    }


def _capability_result(
    *,
    source: str,
    evidence_type: str,
    summary: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source": source,
        "type": evidence_type,
        "summary": summary,
        "evidence": evidence,
    }

# ── Discovery 工具 ─────────────────────────────────────────

@tool
@_with_policy_logging("github_search")
def github_search(query: str) -> list[dict[str, Any]]:
    """
    搜索 GitHub 仓库，用于 Research Agent 自主发现候选数据源。

    Args:
        query: 实体名称、技术方向或关键词，例如 "LangGraph"、"AI Agent"。

    返回：最多 2 个最相关的 DiscoveryResult，identifier 为 owner/repo。
    重要：当你需要 GitHub 证据但还不知道 owner/repo 时，必须先调用此工具。
    """
    tool_input = {"query": query}
    blocked = before_tool_call("github_search", tool_input)
    if blocked:
        return _record("github_search", tool_input, blocked, update_policy=False)

    response = github.client.get(
        "/search/repositories",
        params={
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 2,  
        },
    )
    payload = response.json()
    result = [
        discovery_result(
            source="github",
            identifier=item.get("full_name", ""),
            title=item.get("full_name", ""),
            url=item.get("html_url", ""),
            score=float(item.get("stargazers_count", 0) or 0),
            reason=item.get("description") or "GitHub 仓库搜索结果",
        )
        for item in payload.get("items", []) or []
        if item.get("full_name")
    ]
    print("github_search_result: ",result)
    return _record("github_search", tool_input, result)


@tool
@_with_policy_logging("huggingface_search")
def huggingface_search(query: str) -> list[dict]:
    """
    搜索 HuggingFace 模型，用于 Research Agent 自主发现模型/数据集/空间资源。

    Args:
        query: 实体名称、模型名称或技术关键词。

    返回：候选模型 DiscoveryResult，identifier 为 model_id。
    """
    tool_input = {"query": query}
    blocked = before_tool_call("huggingface_search", tool_input)
    if blocked:
        return _record("huggingface_search", tool_input, blocked, update_policy=False)

    url = f"{huggingface.BASE_URL}/api/models"
    response = huggingface.session.get(
        url,
        params={
            "search": query,
            "limit": 5,
            "sort": "downloads",
            "direction": -1,
        },
        timeout=20,
    )
    response.raise_for_status()
    items = response.json()
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
    return _record("huggingface_search", tool_input, result)


@tool
@_with_policy_logging("community_search")
def community_search(query: str, platforms: list[str] | None = None) -> list[dict[str, Any]]:
    """
    搜索社区讨论资源。

    Args:
        query: 搜索关键词。
        platforms: 社区平台列表，例如 ["reddit", "x", "xiaohongshu"]。

    当前为 Agent Reach 接入预留实现，统一返回 DiscoveryResult。
    """
    platforms = platforms or ["reddit", "x", "xiaohongshu"]
    tool_input = {"query": query, "platforms": platforms}

    # Tool 调用前检查：是否应该阻止这次 Discovery
    blocked = before_tool_call("community_search", tool_input)
    if blocked:
        return _record("community_search", tool_input, blocked, update_policy=False)

    result = [
        discovery_result(
            source="community",
            identifier=f"{platform}:pending:{query}",
            title=f"{platform} 社区搜索占位结果",
            url="",
            score=0.0,
            reason="community_search 当前为 Agent Reach 接入预留实现",
        )
        for platform in platforms
    ]
    return _record("community_search", tool_input, result)


@tool
@_with_policy_logging("youtube_search")
def youtube_search(query: str) -> list[dict[str, Any]]:
    """搜索 YouTube 视频资源（占位工具，后续可替换为 Agent Reach 实现）。"""
    tool_input = {"query": query}
    blocked = before_tool_call("youtube_search", tool_input)
    if blocked:
        return _record("youtube_search", tool_input, blocked, update_policy=False)

    result = [
        discovery_result(
            source="youtube",
            identifier=f"youtube:pending:{query}",
            title="YouTube 搜索占位结果",
            url="",
            score=0.0,
            reason="youtube_search 当前为 Agent Reach 接入预留实现",
        )
    ]
    return _record("youtube_search", tool_input, result)


@tool
@_with_policy_logging("web_search")
def web_search(query: str) -> list[dict[str, Any]]:
    """搜索公开 Web 资料（占位工具，正式搜索能力后续接入）。"""
    tool_input = {"query": query}
    blocked = before_tool_call("web_search", tool_input)
    if blocked:
        return _record("web_search", tool_input, blocked, update_policy=False)

    result = [
        discovery_result(
            source="web",
            identifier=f"web:pending:{query}",
            title="Web 搜索占位结果",
            url="",
            score=0.0,
            reason="web_search 当前为 Agent Reach 接入预留实现",
        )
    ]
    return _record("web_search", tool_input, result)


# ── Capability 工具 ─────────────────────────────────────────

@tool
@_with_policy_logging("github_project_profile")
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
    result = _capability_result(
        source="github",
        evidence_type="project_profile",
        summary=summary,
        evidence={
            "repository": repository,
            "readme": readme_content,
        },
    )
    return _record("github_project_profile", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("github_project_health")
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
    result = _capability_result(
        source="github",
        evidence_type="project_health",
        summary=summary,
        evidence={
            "issues": issue_items,
            "pull_requests": pr_items,
            "commit_activity": commit_activity,
        },
    )
    return _record("github_project_health", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("github_release_summary")
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
    result = _capability_result(
        source="github",
        evidence_type="release_summary",
        summary=summary,
        evidence={
            "releases": release_items,
            "planning": planning,
        },
    )
    return _record("github_release_summary", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("github_ecosystem")
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
    result = _capability_result(
        source="github",
        evidence_type="community_evidence",
        summary=summary,
        evidence={
            "discussions": discussions,
            "planning": planning,
        },
    )
    return _record("github_ecosystem", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("huggingface_model_profile")
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
    result = _capability_result(
        source="huggingface",
        evidence_type="model_profile",
        summary=summary,
        evidence={"model": model},
    )
    return _record("huggingface_model_profile", {"model_id": model_id}, result)


@tool
@_with_policy_logging("community_reader")
def community_reader(identifier: str, platform: str = "community") -> dict[str, Any]:
    """读取社区资源内容（当前为 Agent Reach 接入预留实现）。"""
    result = _capability_result(
        source="community",
        evidence_type="community_discussion",
        summary="Community reader not yet available",
        evidence={
            "identifier": identifier,
            "platform": platform,
            "content": "",
        },
    )
    return _record("community_reader", {"identifier": identifier, "platform": platform}, result)


@tool
@_with_policy_logging("webpage_reader")
def webpage_reader(url: str) -> dict[str, Any]:
    """读取网页正文（占位工具，后续可替换为 Web/Agent Reach 实现）。"""
    result = _capability_result(
        source="web",
        evidence_type="webpage",
        summary="Webpage reader not yet available",
        evidence={"url": url, "content": ""},
    )
    return _record("webpage_reader", {"url": url}, result)


@tool
@_with_policy_logging("youtube_transcript")
def youtube_transcript(video_url: str) -> dict[str, Any]:
    """读取 YouTube 视频转写（占位工具，后续可替换为 Agent Reach 实现）。"""
    result = _capability_result(
        source="youtube",
        evidence_type="youtube_transcript",
        summary="YouTube transcript not yet available",
        evidence={"video_url": video_url, "transcript": ""},
    )
    return _record("youtube_transcript", {"video_url": video_url}, result)


TOOLS = [
    # Discovery
    github_search,
    huggingface_search,
    community_search,
    web_search,
    youtube_search,

    # GitHub Capability
    github_project_profile,
    github_project_health,
    github_release_summary,
    github_ecosystem,

    # HuggingFace Capability
    huggingface_model_profile,

    # Community / Web / Video Capability
    community_reader,
    webpage_reader,
    youtube_transcript,
]



# ── 底层工具 暂时不用（Internal Tool）─────────────────────────────────
# 这些是底层 GitHub API 工具，不暴露给 Agent（不在 TOOLS 列表里）。
# Capability Tool 内部直接调 github.xxx()，不需要这些 @tool 包装。
# 如果以后需要单独暴露给 Agent，再取消注释即可。

# @tool
# @_with_policy_logging("get_repository_info")
# def get_repository_info(owner: str, repo: str):
#     result = github.get_repository(owner, repo)
#     return _record("get_repository_info", {"owner": owner, "repo": repo}, result)

# @tool
# @_with_policy_logging("readme")
# def readme(owner: str, repo: str):
#     result = github.get_readme(owner, repo)
#     return _record("readme", {"owner": owner, "repo": repo}, result)

# @tool
# @_with_policy_logging("releases")
# def releases(owner: str, repo: str):
#     result = github.get_releases(owner, repo)
#     return _record("releases", {"owner": owner, "repo": repo}, result)

# @tool
# @_with_policy_logging("issues")
# def issues(owner: str, repo: str):
#     result = github.get_issues(owner, repo)
#     return _record("issues", {"owner": owner, "repo": repo}, result)

# @tool
# @_with_policy_logging("pull_requests")
# def pull_requests(owner: str, repo: str):
#     result = github.get_pull_requests(owner, repo)
#     return _record("pull_requests", {"owner": owner, "repo": repo}, result)

# @tool
# @_with_policy_logging("get_commit_activity")
# def get_commit_activity(owner: str, repo: str) -> dict:
#     result = github.get_commit_activity(owner, repo)
#     return _record("get_commit_activity", {"owner": owner, "repo": repo}, result)

# @tool
# @_with_policy_logging("get_planning_signals")
# def get_planning_signals(owner: str, repo: str) -> dict:
#     result = github.get_planning_signals(owner, repo)
#     return _record("get_planning_signals", {"owner": owner, "repo": repo}, result)

# @tool
# @_with_policy_logging("get_discussion_signals")
# def get_discussion_signals(owner: str, repo: str) -> dict:
#     result = github.get_discussion_signals(owner, repo)
#     return _record("get_discussion_signals", {"owner": owner, "repo": repo}, result)
