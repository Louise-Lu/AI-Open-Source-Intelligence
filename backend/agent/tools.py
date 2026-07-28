from functools import wraps
from typing import Any

from langchain_core.tools import tool

from agent.discovery import discovery_result
from agent.research_policy import after_tool_call, before_tool_call, build_policy_hint
from agent.trace import add_trace
from sources.github.client import GitHubAPI
from sources.huggingface.client import HuggingFaceClient

github = GitHubAPI()
huggingface = HuggingFaceClient()


def _print_policy_hint(label: str, tool_name: str) -> None:
    print(f"\n========== POLICY {label}: {tool_name} ==========")
    print(build_policy_hint())


def _with_policy_logging(tool_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _print_policy_hint("BEFORE", tool_name)
            return func(*args, **kwargs)

        return wrapper

    return decorator

# _record 更新 Policy 和 Trace
def _record(tool_name: str, tool_input: dict, tool_output, *, update_policy: bool = True):

    if update_policy:
        # 更新 policy的state 
        after_tool_call(tool_name, tool_output)
    # 更新 trace 
    add_trace(tool_name, tool_input, tool_output)
    
    _print_policy_hint("AFTER", tool_name)
    return tool_output


def _github_repository_raw(owner: str, repo: str) -> dict[str, Any]:
    return github.get_repository(owner, repo)


def _github_readme_raw(owner: str, repo: str) -> str:
    return github.get_readme(owner, repo)


def _github_releases_raw(owner: str, repo: str):
    return github.get_releases(owner, repo)


def _github_issues_raw(owner: str, repo: str):
    return github.get_issues(owner, repo)


def _github_pull_requests_raw(owner: str, repo: str):
    return github.get_pull_requests(owner, repo)


def _github_commit_activity_raw(owner: str, repo: str) -> dict[str, Any]:
    return github.get_commit_activity(owner, repo)


def _github_planning_signals_raw(owner: str, repo: str) -> dict[str, Any]:
    return github.get_planning_signals(owner, repo)


def _github_discussion_signals_raw(owner: str, repo: str) -> dict[str, Any]:
    return github.get_discussion_signals(owner, repo)


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
@_with_policy_logging("get_repository_info")
def get_repository_info(owner: str, repo: str):
    """
    获取 GitHub 仓库的基础元数据。仅当用户询问具体数字时才需调用，读取 README 时不必额外调用。
    返回：full_name, description, language, stars, forks, topics, license, created_at, updated_at。
    适用场景：用户询问仓库的基本信息，如"这个项目的语言是什么？"、"有多少 star？"。
    不包含：README, Issue, Release
    """
    result = _github_repository_raw(owner, repo)
    return _record("get_repository_info", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("readme")
def readme(owner: str, repo: str):
    """获取仓库的 README 全文。

    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"

    适用场景：用户想了解项目的用途、用法、安装方式等。想"看一下 README"、"这个项目是干什么的？"。
    调用后即可直接根据 README 内容回答，无需再调用其他工具。
    """
    result = _github_readme_raw(owner, repo)
    return _record("readme", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("releases")
def releases(owner: str, repo: str):
    """
    获取仓库的最近 Releases 版本发布列表。
    用于：查看版本号、查看发布时间、查看 release notes。
    不用于：star、fork、README、仓库基本信息。
    每个 Release 包含: tag_name, name, published_at, body。
    适用场景：用户询问"最新版本是什么？"、"最近更新了哪些功能？"。
    """
    result = _github_releases_raw(owner, repo)
    return _record("releases", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("issues")
def issues(owner: str, repo: str):
    """获取 Issues 列表

    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"

    每个 Issue 包含: title, state, created_at, comments。
    适用场景：用户询问"当前有哪些待解决的问题？"或"社区反馈了什么？"。
    重要：调用后直接基于返回的列表回答用户问题，无需再调用 get_repository 等其他工具补充背景。
    注意：结果已自动过滤掉 Pull Request。
    """
    result = _github_issues_raw(owner, repo)
    return _record("issues", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("pull_requests")
def pull_requests(owner: str, repo: str):
    """获取 Pull Requests 列表

    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"

    每个 PR 包含: title, state, created_at, merged (布尔值)。
    适用场景：用户询问"最近合并了哪些功能？"或"开发进度如何？"。
    """
    result = _github_pull_requests_raw(owner, repo)
    return _record("pull_requests", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("get_commit_activity")
def get_commit_activity(owner: str, repo: str) -> dict:
    """
    获取仓库近期的提交活跃度统计。
    返回：commits_last_30_days（近30天提交数）, commits_last_90_days（近90天提交数）, active_contributors_count（活跃贡献者数）。
    适用场景：用户询问"这个项目还活跃吗？"、"最近开发节奏怎么样？"。
    """
    result = _github_commit_activity_raw(owner, repo)
    return _record("get_commit_activity", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("get_planning_signals")
def get_planning_signals(owner: str, repo: str) -> dict:
    """
    获取仓库的显性规划信号，包括：
    - roadmap_text: ROADMAP.md 的全文
    - milestones: 开放的里程碑及其进度
    - enhancement_issues: 带 enhancement / proposal 标签的 Issue 标题
    适用场景：用户询问"项目未来的计划是什么？"、"下一个里程碑是什么？"。
    """
    result = _github_planning_signals_raw(owner, repo)
    return _record("get_planning_signals", {"owner": owner, "repo": repo}, result)


@tool
@_with_policy_logging("get_discussion_signals")
def get_discussion_signals(owner: str, repo: str) -> dict:
    """
    获取仓库的社区讨论信号。
    返回：hot_topics 列表，每个话题包含标题及是否有官方回答/维护者参与。
    适用场景：用户想了解"社区最近在热议什么？"或"官方有没有对某个问题做出回应？"。
    注意：仅当仓库启用了 Discussions 功能时有数据。
    """
    result = _github_discussion_signals_raw(owner, repo)
    return _record("get_discussion_signals", {"owner": owner, "repo": repo}, result)


# ── Capability 工具 ─────────────────────────────────────────

@tool
@_with_policy_logging("github_project_profile")
def github_project_profile(owner: str, repo: str) -> dict[str, Any]:
    """
    获取 GitHub 项目的基础画像证据。

    自动聚合 repository + README，返回统一 Capability Evidence。
    当需要了解项目定位、用途、技术栈、基础元数据时使用。
    """
    repository = _github_repository_raw(owner, repo)
    readme_content = _github_readme_raw(owner, repo)
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
    issue_items = _github_issues_raw(owner, repo)
    pr_items = _github_pull_requests_raw(owner, repo)
    commit_activity = _github_commit_activity_raw(owner, repo)
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
    release_items = _github_releases_raw(owner, repo)
    planning = _github_planning_signals_raw(owner, repo)
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
    discussions = _github_discussion_signals_raw(owner, repo)
    planning = _github_planning_signals_raw(owner, repo)
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
