from fastapi import APIRouter

from pydantic import BaseModel

from services.entity_adapter import EntityAdapter
from services.report_pipeline import ReportPipeline


router = APIRouter(prefix="/release-diff", tags=["Release Diff"])
adapter = EntityAdapter()
pipeline = ReportPipeline()


class ReleaseDiffRequest(BaseModel):

    owner: str

    repo: str

    old_tag: str

    new_tag: str


@router.post("")
def release_diff(request: ReleaseDiffRequest):
    entity = adapter.from_owner_repo(request.owner, request.repo)
    return {
        "comparison": pipeline.generate_release_diff(
            entity,
            request.old_tag,
            request.new_tag,
        )
    }
