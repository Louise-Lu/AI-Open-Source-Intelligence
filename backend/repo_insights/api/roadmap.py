from fastapi import APIRouter
from repo_insights.services.entity_adapter import EntityAdapter
from repo_insights.services.report_pipeline import ReportPipeline

router = APIRouter(tags=["Roadmap"])
adapter = EntityAdapter()
pipeline = ReportPipeline()

@router.get(
"/repositories/{owner}/{repo}/roadmap"
)
def roadmap(owner:str, repo:str):
    entity = adapter.from_owner_repo(owner, repo)
    return pipeline.generate_report(entity, "roadmap")
