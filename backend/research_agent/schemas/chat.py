from typing import Any

from pydantic import BaseModel, Field


class ChatTrace(BaseModel):
    intent: dict[str, Any] = Field(default_factory=dict)
    discovered_sources: dict[str, list[Any]] = Field(default_factory=dict)
    # react_steps 是前端展示 Thought / Action / Observation 的 ReAct 步骤。
    # steps 暂时保留，兼容现有前端组件。
    steps: list[dict[str, Any]] = Field(default_factory=list)
    react_steps: list[dict[str, Any]] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    trace: ChatTrace
    error: str | None = None
