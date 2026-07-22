from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TaskRoute(BaseModel):
    task: Literal[
        "single_project_analysis",
        "project_comparison",
        "project_search",
        "update_tracking",
        "general_question",
    ]
    reports: list[Literal[
        "profile",
        "project_health",
        "analysis",
        "roadmap",
        "comparison",
        "recommendation",
        "release_diff",
    ]] = Field(default_factory=list)
    need_entity_resolution: bool = False
    confidence: float = 0.0
