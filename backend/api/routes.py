from fastapi import APIRouter

from tools.github import GitHubAPI

router = APIRouter()
github = GitHubAPI()


@router.get("/")
def root():
    return {"message": "GitHub Intelligence Agent is running!"}


@router.get("/repo/{owner}/{repo}")
def repository(owner:str, repo:str):

    repo_info = github.get_repository(owner, repo)
    return repo_info

@router.get("/readme/{owner}/{repo}")
def readme(owner: str, repo: str):

    return {
        "content": github.get_readme(owner, repo)
    }

@router.get("/releases/{owner}/{repo}")
def releases(owner: str, repo: str):

    releases = github.get_releases(owner, repo)
    return releases


@router.get("/issues/{owner}/{repo}")
def issues(owner: str, repo: str, state: str = "open", page: int = 1, per_page: int = 30):
    issues = github.get_issues(owner, repo)
    return issues


@router.get("/pulls/{owner}/{repo}")
def pull_requests(
    owner: str, repo: str, state: str = "open", page: int = 1, per_page: int = 30
):  
    pull_requests = github.get_pull_requests(owner, repo)
    return pull_requests


# @router.get("/contributors/{owner}/{repo}")
# def contributors(owner: str, repo: str, anon: bool = False, page: int = 1, per_page: int = 30):
#     return {
#         "contributors": github.list_contributors(
#             owner=owner,
#             repo=repo,
#             anon=anon,
#             page=page,
#             per_page=per_page,
#         )
#     }
