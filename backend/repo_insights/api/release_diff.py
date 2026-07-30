from fastapi import APIRouter

from repo_insights.services.entity_adapter import EntityAdapter
from repo_insights.services.report_pipeline import ReportPipeline


router = APIRouter(prefix="/release-diff", tags=["Release Diff"])
adapter = EntityAdapter()
pipeline = ReportPipeline()


@router.get("/repositories/{owner}/{repo}/releases/diff")
def release_diff(owner: str, repo: str, old_tag: str, new_tag: str):
    entity = adapter.from_owner_repo(owner, repo)
    return {
        "comparison": pipeline.generate_release_diff(
            entity,
            old_tag,
            new_tag,
        )
    }
