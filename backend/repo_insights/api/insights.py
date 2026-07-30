from fastapi import APIRouter

from repo_insights.services.entity_adapter import EntityAdapter
from repo_insights.services.report_pipeline import ReportPipeline

router = APIRouter(tags=["Insights"])
adapter = EntityAdapter()
pipeline = ReportPipeline()


@router.get("/repositories/{owner}/{repo}/insights")
def get_insights(owner: str, repo: str):
    """一次请求：收集证据 + 并发生成 Profile / Roadmap / Analysis。"""
    entity = adapter.from_owner_repo(owner, repo)
    return pipeline.generate_all(entity)
