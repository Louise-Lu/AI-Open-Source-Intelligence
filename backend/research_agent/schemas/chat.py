from typing import Any

from pydantic import BaseModel, Field


class ChatTrace(BaseModel):
    intent: dict[str, Any] = Field(default_factory=dict)
    discovered_sources: dict[str, list[Any]] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    trace: ChatTrace
    error: str | None = None
