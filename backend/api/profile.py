from fastapi import APIRouter

from services.profile_service import RepositoryProfileService


router = APIRouter(tags=["Profile"])

service = RepositoryProfileService()


@router.get("/repositories/{owner}/{repo}/profile")
def get_profile(owner: str, repo: str):
    return service.generate(owner, repo)
