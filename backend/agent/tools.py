# from langchain_core.tools import tool

# from tools.github.client import GitHubAPI

# github = GitHubAPI()


# @tool
# def repository_tool(owner: str, repo: str):
#     """Get GitHub repository metadata."""
#     return github.get_repository(owner, repo)


# @tool
# def readme_tool(owner: str, repo: str):
#     """Get repository README."""
#     return github.get_readme(owner, repo)

# @tool
# def release_tool(owner: str, repo: str):
#     """ Release helper."""
#     return github.get_release(owner, repo)

# @tool
# def pull_request_tool(owner: str, repo: str):
#     """Pull request helper methods."""
#     return github.get_pull_request(owner, repo)

# TOOLS = [
#     repository_tool,
#     readme_tool,
#     release_tool,
#     pull_request_tool,
# ]