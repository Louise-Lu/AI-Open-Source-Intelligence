from fastapi import APIRouter

from repo_insights.services.entity_adapter import EntityAdapter
from repo_insights.services.report_pipeline import ReportPipeline


router = APIRouter(tags=["Compare"])

adapter = EntityAdapter()
pipeline = ReportPipeline()

@router.get("/repositories/compare")
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


    entity1 = adapter.from_owner_repo(owner1, name1)
    entity2 = adapter.from_owner_repo(owner2, name2)
    
    return pipeline.generate_comparison(entity1, entity2)