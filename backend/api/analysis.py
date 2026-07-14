from fastapi import APIRouter

from services.analysis_service import RepositoryAnalysisService


router = APIRouter(tags=["Analysis"])

service = RepositoryAnalysisService()


@router.get("/repositories/{owner}/{repo}/analysis")
def analyze_repository(owner: str, repo: str):
    """Run a one-shot repository analysis through the existing Agent."""
    return service.analyze(owner, repo)
