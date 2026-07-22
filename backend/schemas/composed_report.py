from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReportContext(BaseModel):
    project_name: str
    reports: dict[str, Any] = Field(default_factory=dict)


class ComposedAnswer(BaseModel):
    answer: str
