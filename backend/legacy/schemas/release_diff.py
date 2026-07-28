from pydantic import BaseModel


class ReleaseDiffEvidence(BaseModel):
    """两个 Release 的结构化证据"""

    old_tag: str
    new_tag: str

    old_body: str | None = None
    new_body: str | None = None