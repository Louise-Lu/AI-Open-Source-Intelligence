from fastapi import APIRouter

from services.comparison_service import RepositoryComparisonService


router = APIRouter(tags=["Compare"])

service = RepositoryComparisonService()


@router.get("/compare")
def compare_repositories(
    repo1: str,
    repo2: str,
):
    """
    repo1=langchain-ai/langgraph
    repo2=microsoft/autogen
    """

    owner1, name1 = repo1.split("/")
    owner2, name2 = repo2.split("/")

    return service.compare(
        owner1,
        name1,
        owner2,
        name2,
    )
