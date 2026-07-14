from fastapi import APIRouter

from services.analysis_service import RepositoryAnalysisService
from tools.github import GitHubAPI

router = APIRouter()

github = GitHubAPI()
analysis_service = RepositoryAnalysisService()


@router.get("/")
def root():
    return {"message": "GitHub Intelligence Agent is running!"}


@router.get("/repo/{owner}/{repo}")
def get_repo(owner: str, repo: str):

    data = github.get_repository(owner, repo)

    return {
        "name": data["name"],
        "owner": data["owner"]["login"],
        "description": data["description"],
        "stars": data["stargazers_count"],
        "language": data["language"],
        "default_branch": data["default_branch"],
    }

@router.get("/readme/{owner}/{repo}")
def readme(owner: str, repo: str):

    return {
        "content": github.get_readme(owner, repo)
    }


@router.get("/releases/{owner}/{repo}")
def releases(owner: str, repo: str):
    return {"releases": github.get_release(owner, repo)}


@router.get("/issues/{owner}/{repo}")
def issues(owner: str, repo: str, state: str = "open", page: int = 1, per_page: int = 30):
    return {
        "issues": github.list_issues(
            owner=owner,
            repo=repo,
            state=state,
            page=page,
            per_page=per_page,
        )
    }


@router.get("/pulls/{owner}/{repo}")
def pull_requests(
    owner: str, repo: str, state: str = "open", page: int = 1, per_page: int = 30
):
    return {
        "pull_requests": github.list_pull_requests(
            owner=owner,
            repo=repo,
            state=state,
            page=page,
            per_page=per_page,
        )
    }


@router.get("/contributors/{owner}/{repo}")
def contributors(owner: str, repo: str, anon: bool = False, page: int = 1, per_page: int = 30):
    return {
        "contributors": github.list_contributors(
            owner=owner,
            repo=repo,
            anon=anon,
            page=page,
            per_page=per_page,
        )
    }


@router.get("/analysis/{owner}/{repo}")
def analyze_repository(owner: str, repo: str):
    """Run a one-shot repository analysis through the existing Agent."""
    return {"analysis": analysis_service.analyze(owner, repo)}
