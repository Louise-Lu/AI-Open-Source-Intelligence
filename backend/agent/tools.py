from langchain_core.tools import tool

from agent.trace import add_trace
from sources.github.client import GitHubAPI
from sources.huggingface.client import HuggingFaceClient

github = GitHubAPI()
huggingface = HuggingFaceClient()


def _record(tool_name: str, tool_input: dict, tool_output):
    add_trace(tool_name, tool_input, tool_output)
    return tool_output


# ── 底层数据工具 ─────────────────────────────────────────────

@tool
def github_search(query: str) -> list[str]:
    """
    搜索 GitHub 仓库，用于 Research Agent 自主发现候选数据源。

    Args:
        query: 实体名称、技术方向或关键词，例如 "LangGraph"、"AI Agent"。

    返回：最多 2 个最相关的候选仓库 owner/repo 列表，例如 ["crewAIInc/crewAI"]。
    重要：当你需要 GitHub 证据但还不知道 owner/repo 时，必须先调用此工具。
    """
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
        item.get("full_name")
        for item in payload.get("items", []) or []
        if item.get("full_name")
    ]
    return _record("github_search", {"query": query}, result)


@tool
def huggingface_search(query: str) -> list[dict]:
    """
    搜索 HuggingFace 模型，用于 Research Agent 自主发现模型/数据集/空间资源。

    Args:
        query: 实体名称、模型名称或技术关键词。

    返回：候选模型列表，每项包含 id, downloads, likes, pipeline_tag, tags。
    """
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
        {
            "id": item.get("id"),
            "downloads": item.get("downloads", 0),
            "likes": item.get("likes", 0),
            "pipeline_tag": item.get("pipeline_tag"),
            "tags": item.get("tags", []),
        }
        for item in items or []
        if item.get("id")
    ]
    return _record("huggingface_search", {"query": query}, result)


@tool
def get_repository_info(owner: str, repo: str):
    """
    获取 GitHub 仓库的基础元数据。仅当用户询问具体数字时才需调用，读取 README 时不必额外调用。
    返回：full_name, description, language, stars, forks, topics, license, created_at, updated_at。
    适用场景：用户询问仓库的基本信息，如"这个项目的语言是什么？"、"有多少 star？"。
    不包含：README, Issue, Release
    """
    result = github.get_repository(owner, repo)
    return _record("get_repository_info", {"owner": owner, "repo": repo}, result)


@tool
def readme(owner: str, repo: str):
    """获取仓库的 README 全文。

    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"

    适用场景：用户想了解项目的用途、用法、安装方式等。想"看一下 README"、"这个项目是干什么的？"。
    调用后即可直接根据 README 内容回答，无需再调用其他工具。
    """
    result = github.get_readme(owner, repo)
    return _record("readme", {"owner": owner, "repo": repo}, result)


@tool
def releases(owner: str, repo: str):
    """
    获取仓库的最近 Releases 版本发布列表。
    用于：查看版本号、查看发布时间、查看 release notes。
    不用于：star、fork、README、仓库基本信息。
    每个 Release 包含: tag_name, name, published_at, body。
    适用场景：用户询问"最新版本是什么？"、"最近更新了哪些功能？"。
    """
    result = github.get_releases(owner, repo)
    return _record("releases", {"owner": owner, "repo": repo}, result)


@tool
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
    result = github.get_issues(owner, repo)
    return _record("issues", {"owner": owner, "repo": repo}, result)


@tool
def pull_requests(owner: str, repo: str):
    """获取 Pull Requests 列表

    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"

    每个 PR 包含: title, state, created_at, merged (布尔值)。
    适用场景：用户询问"最近合并了哪些功能？"或"开发进度如何？"。
    """
    result = github.get_pull_requests(owner, repo)
    return _record("pull_requests", {"owner": owner, "repo": repo}, result)


@tool
def get_commit_activity(owner: str, repo: str) -> dict:
    """
    获取仓库近期的提交活跃度统计。
    返回：commits_last_30_days（近30天提交数）, commits_last_90_days（近90天提交数）, active_contributors_count（活跃贡献者数）。
    适用场景：用户询问"这个项目还活跃吗？"、"最近开发节奏怎么样？"。
    """
    result = github.get_commit_activity(owner, repo)
    return _record("get_commit_activity", {"owner": owner, "repo": repo}, result)


@tool
def get_planning_signals(owner: str, repo: str) -> dict:
    """
    获取仓库的显性规划信号，包括：
    - roadmap_text: ROADMAP.md 的全文
    - milestones: 开放的里程碑及其进度
    - enhancement_issues: 带 enhancement / proposal 标签的 Issue 标题
    适用场景：用户询问"项目未来的计划是什么？"、"下一个里程碑是什么？"。
    """
    result = github.get_planning_signals(owner, repo)
    return _record("get_planning_signals", {"owner": owner, "repo": repo}, result)


@tool
def get_discussion_signals(owner: str, repo: str) -> dict:
    """
    获取仓库的社区讨论信号。
    返回：hot_topics 列表，每个话题包含标题及是否有官方回答/维护者参与。
    适用场景：用户想了解"社区最近在热议什么？"或"官方有没有对某个问题做出回应？"。
    注意：仅当仓库启用了 Discussions 功能时有数据。
    """
    result = github.get_discussion_signals(owner, repo)
    return _record("get_discussion_signals", {"owner": owner, "repo": repo}, result)


@tool
def reddit_search(query: str) -> str:
    """搜索 Reddit 社区讨论（占位工具，正式搜索能力后续接入）。"""
    result = "Reddit search not yet available"
    return _record("reddit_search", {"query": query}, result)


@tool
def web_search(query: str) -> str:
    """搜索公开 Web 资料（占位工具，正式搜索能力后续接入）。"""
    result = "Web search not yet available"
    return _record("web_search", {"query": query}, result)


TOOLS = [
    github_search,
    huggingface_search,
    get_repository_info,
    readme,
    releases,
    issues,
    pull_requests,
    get_commit_activity,
    get_planning_signals,
    get_discussion_signals,
    reddit_search,
    web_search,
]
