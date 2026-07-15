from langchain_core.tools import tool

from tools.github.client import GitHubAPI

github = GitHubAPI()

@tool
def get_repository_info(owner:str, repo:str):
    """
    获取 GitHub 仓库基础信息。

    适用于：
    - star 数量
    - fork 数量
    - language
    - license
    - topics
    - created_at
    - updated_at

    不包含：
    - README
    - Issue
    - Release
    """

    return github.get_repository(owner, repo)


@tool
def readme(owner: str, repo: str):
    """获取 README 内容
    
    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"
    """
    return github.get_readme(owner, repo)


@tool
def releases(owner: str, repo: str):
    """
    获取 GitHub Repository 的 Release 信息。

    用于：
    - 查看版本号
    - 查看发布时间
    - 查看 release notes

    不用于：
    - star
    - fork
    - README
    - 仓库基本信息
    """
    return github.get_releases(owner, repo)


@tool
def issues(owner: str, repo: str):
    """获取 Issues 列表
    
    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"
    """
    return github.get_issues(owner, repo)


@tool
def pull_requests(owner: str, repo: str):
    """获取 Pull Requests 列表
    
    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"
    """
    return github.get_pull_requests(owner, repo)


# @tool
# def contributors(owner: str, repo: str):
#     """获取 Contributors 列表
    
#     Args:
#         owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
#         repo: GitHub 仓库名称，例如 "langgraph"
#     """
#     return github.list_contributors(owner, repo)

TOOLS = [
    get_repository_info,
    readme,
    releases,
    issues,
    pull_requests,
    # contributors,
]