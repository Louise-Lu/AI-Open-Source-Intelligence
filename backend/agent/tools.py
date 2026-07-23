from langchain_core.tools import tool

from sources.github.client import GitHubAPI
from services.analysis_service import RepositoryAnalysisService
from services.profile_service import RepositoryProfileService
# from services.release_diff_service import ReleaseDiffService
from services.comparison_service import RepositoryComparisonService
from services.roadmap_service import RepositoryRoadmapService

github = GitHubAPI()

# 底层数据工具
@tool
def get_repository_info(owner:str, repo:str):
    """
    获取 GitHub 仓库的基础元数据。仅当用户询问具体数字时才需调用，读取 README 时不必额外调用。

    返回：full_name, description, language, stars, forks, topics, license, created_at, updated_at。

    适用场景：用户询问仓库的基本信息，如“这个项目的语言是什么？”、“有多少 star？”。

    不包含：README, Issue, Release
    """
    return github.get_repository(owner, repo)


@tool
def readme(owner: str, repo: str):
    """获取仓库的 README 全文。
    
    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"

    适用场景：用户想了解项目的用途、用法、安装方式等。想“看一下 README”、“这个项目是干什么的？”。
    调用后即可直接根据 README 内容回答，无需再调用其他工具。
    """
    return github.get_readme(owner, repo)


@tool
def releases(owner: str, repo: str):
    """
    获取仓库的最近 Releases 版本发布 列表。

    用于：
    - 查看版本号
    - 查看发布时间
    - 查看 release notes

    不用于：
    - star
    - fork
    - README
    - 仓库基本信息


    每个 Release 包含: tag_name, name, published_at, body。
    适用场景：用户询问“最新版本是什么？”、“最近更新了哪些功能？”。
    """
    return github.get_releases(owner, repo)


@tool
def issues(owner: str, repo: str):
    """获取 Issues 列表
    
    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"
        获取仓库的 Issues 列表。
    
    每个 Issue 包含: title, state, created_at, comments。
    适用场景：用户询问“当前有哪些待解决的问题？”或“社区反馈了什么？”。
    重要：调用后直接基于返回的列表回答用户问题，无需再调用 get_repository 等其他工具补充背景。
    注意：结果已自动过滤掉 Pull Request。
    """
    return github.get_issues(owner, repo)


@tool
def pull_requests(owner: str, repo: str):
    """获取 Pull Requests 列表
    
    Args:
        owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
        repo: GitHub 仓库名称，例如 "langgraph"

    每个 PR 包含: title, state, created_at, merged (布尔值)。
    适用场景：用户询问“最近合并了哪些功能？”或“开发进度如何？”。

    """
    return github.get_pull_requests(owner, repo)

@tool
def get_commit_activity(owner: str, repo: str) -> dict:
    """
    获取仓库近期的提交活跃度统计。
    返回：commits_last_30_days（近30天提交数）, commits_last_90_days（近90天提交数）, active_contributors_count（活跃贡献者数）。
    适用场景：用户询问“这个项目还活跃吗？”、“最近开发节奏怎么样？”。
    """
    return github.get_commit_activity(owner, repo)

@tool
def get_planning_signals(owner: str, repo: str) -> dict:
    """
    获取仓库的显性规划信号，包括：
    - roadmap_text: ROADMAP.md 的全文
    - milestones: 开放的里程碑及其进度
    - enhancement_issues: 带 enhancement / proposal 标签的 Issue 标题
    适用场景：用户询问“项目未来的计划是什么？”、“下一个里程碑是什么？”。
    """
    return github.get_planning_signals(owner, repo)

@tool
def get_discussion_signals(owner: str, repo: str) -> dict:
    """
    获取仓库的社区讨论信号。
    返回：hot_topics 列表，每个话题包含标题及是否有官方回答/维护者参与。
    适用场景：用户想了解“社区最近在热议什么？”或“官方有没有对某个问题做出回应？”。
    注意：仅当仓库启用了 Discussions 功能时有数据。
    """
    return github.get_discussion_signals(owner, repo)


# @tool
# def contributors(owner: str, repo: str):
#     """获取 Contributors 列表
    
#     Args:
#         owner: GitHub 仓库的所有者用户名，例如 "langchain-ai"
#         repo: GitHub 仓库名称，例如 "langgraph"
#     """
#     return github.list_contributors(owner, repo)


# 高级分析工具
@tool
def analyze_repository(owner: str, repo: str) -> str:
    """
    对 GitHub 仓库进行深度分析，生成 Markdown 格式的综合报告。
   【自包含分析工具】本工具会自动收集仓库所有必要数据（基本信息、README、Releases、Issues、PR、提交活跃度、规划信号、社区讨论），
    并生成一份全面的深度分析报告。
    重要：请直接调用，无需提前获取任何数据；调用后直接使用报告内容回答用户。
    报告涵盖：项目定位、技术特点、社区情况、企业成熟度、未来发展方向。
    适用场景：用户要求“全面分析一个项目”、“帮我看看这个仓库值不值得用”等需要深入解读的场合。
    本工具已整合所有必要数据，调用后请直接基于返回的报告回答用户，
    """
    return RepositoryAnalysisService().analyze(owner, repo)


@tool
def get_repository_profile(owner: str, repo: str) -> dict:
    """
    【自包含分析工具】无需提前拉数据
    生成仓库的结构化画像，包含维护分数、企业分数、社区分数、项目摘要和推荐场景。
    返回纯 JSON，适合前端渲染卡片或进行仓库排序比较。
    适用场景：用户问“这个项目成熟度怎么样？”或想快速了解一个仓库的关键指标。
    本工具已整合所有必要数据，调用后请直接基于返回的报告回答用户，
    """
    return RepositoryProfileService().generate(owner, repo)


@tool
def compare_repositories(owner1: str, repo1: str, owner2: str, repo2: str) -> dict:
    """
   【自包含分析工具】无需提前拉数据
    从项目定位、技术路线、社区活跃度、企业成熟度、推荐场景等多个维度对比两个 GitHub 仓库。
    返回结构化 JSON。
    适用场景：用户问“LangGraph 和 AutoGen 哪个更适合我？”等二选一或多选问题。
    本工具已整合所有必要数据，调用后请直接基于返回的报告回答用户，
    """
    return RepositoryComparisonService().compare(owner1, repo1, owner2, repo2)


# @tool
# def diff_releases(owner: str, repo: str, tag1: str, tag2: str) -> dict:
#     """
#     比较两个 Release 版本的差异，总结 New Features、Improvements、Bug Fixes、Breaking Changes 以及升级建议。
#     适用场景：用户询问“v1.2 和 v1.3 有什么区别？”、“升级到这个版本有没有风险？”。
#     """
#     return ReleaseDiffService().diff(owner, repo, tag1, tag2)


@tool
def predict_roadmap(owner: str, repo: str) -> dict:
    """
    【自包含分析工具】无需提前拉数据
    基于显性规划、隐性动态、社区脉搏三层情报，预测仓库的未来路线图。
    返回 JSON，包含当前阶段、近期方向、3/6-12个月预测、机会、风险及推理依据。
    适用场景：用户想提前了解项目未来走向，判断是否值得长期投入。
    本工具已整合所有必要数据，调用后请直接基于返回的报告回答用户，
    """
    return RepositoryRoadmapService().predict(owner, repo)


TOOLS = [
    get_repository_info,
    readme,
    releases,
    issues,
    pull_requests,
    # contributors,
    get_commit_activity,
    get_planning_signals,
    get_discussion_signals,
    # analyze_repository,
    # get_repository_profile,
    # compare_repositories,
    # predict_roadmap,
]