from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TaskRoute(BaseModel):

    task: Literal[
        "single_project_analysis",
        "project_comparison",
        "project_update",
        "market_intelligence",
        "deep_research",
        "general_question"
    ]

    features:list[str]

    depth:Literal[
        "quick",
        "standard",
        "deep"
    ]
