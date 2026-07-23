from __future__ import annotations

from pydantic import BaseModel, Field


class HuggingFaceModelInfo(BaseModel):
    downloads: int = 0
    likes: int = 0
    pipeline_tag: str | None = None
    tags: list[str] = Field(default_factory=list)
    last_modified: str | None = None
