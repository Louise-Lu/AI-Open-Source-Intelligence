from fastapi import APIRouter

from services.analysis_service import RepositoryAnalysisService

router = APIRouter(tags=["Analysis"])

service = RepositoryAnalysisService()


@router.get("/repositories/{owner}/{repo}/analysis")
def analyze_repository(owner: str, repo: str):

    analysis = service.analyze(owner, repo)

    return {
        "analysis": analysis
    }

