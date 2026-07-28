from fastapi import APIRouter
from legacy.services.entity_adapter import EntityAdapter
from legacy.services.report_pipeline import ReportPipeline

router = APIRouter(tags=["Roadmap"])
adapter = EntityAdapter()
pipeline = ReportPipeline()

@router.get(
"/repositories/{owner}/{repo}/roadmap"
)
def roadmap(owner:str, repo:str):
    entity = adapter.from_owner_repo(owner, repo)
    return pipeline.generate_report(entity, "roadmap")
