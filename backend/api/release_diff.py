from fastapi import APIRouter

from pydantic import BaseModel

from services.release_diff_service import ReleaseDiffService


router = APIRouter(prefix="/release-diff", tags=["Release Diff"])


service = ReleaseDiffService()


class ReleaseDiffRequest(BaseModel):

    owner: str

    repo: str

    old_tag: str

    new_tag: str


@router.post("")
def release_diff(request: ReleaseDiffRequest):
    return {
        "comparison": service.compare(
            request.owner,
            request.repo,
            request.old_tag,
            request.new_tag,
        )
    }
