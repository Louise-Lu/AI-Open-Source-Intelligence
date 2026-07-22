from typing import Literal, Optional

from pydantic import BaseModel


class TaskRoute(BaseModel):
    route: Literal[
        "profile",
        "roadmap",
        "comparison",
        "release_diff",
        "analysis_report",
        "agent",
    ]
    reason: Optional[str] = None
