from fastapi import APIRouter
# 1. owner/repo -> entity 
# 2. 生成 analysis报告
from legacy.services.entity_adapter import EntityAdapter
from legacy.services.report_pipeline import ReportPipeline

router = APIRouter(tags=["Analysis"])
adapter = EntityAdapter()
pipeline = ReportPipeline()


@router.get("/repositories/{owner}/{repo}/analysis")
def analyze_repository(owner: str, repo: str):
    entity = adapter.from_owner_repo(owner, repo)
    analysis = pipeline.generate_report(entity, "analysis")

    return {
        "analysis": analysis
    }
