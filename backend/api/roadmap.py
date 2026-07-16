from fastapi import APIRouter
from services.roadmap_service import RepositoryRoadmapService

router = APIRouter(tags=["Roadmap"])

service = RepositoryRoadmapService()

@router.get(
"/repositories/{owner}/{repo}/roadmap"
)
def roadmap(owner:str, repo:str):

    result = service.predict(
        owner,
        repo
    )

    return result