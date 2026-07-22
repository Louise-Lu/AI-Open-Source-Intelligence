from pydantic import BaseModel, Field
from typing import Any

class ChatTrace(BaseModel):
    task: dict[str, Any] = Field(default_factory=dict)
    entity: dict[str, Any] = Field(default_factory=dict)

class ChatRequest(BaseModel):
    message: str
    owner: str
    repo: str

# ChatResponse 定义返回数据的格式 ：返回给前端的 JSON 结构。
# 包含4个字段：answer（回答内容）、trace（调用链追踪，调试用）、
# task（如果是特定任务如 roadmap，会返回对应的任务数据）entity 任务主体。
class ChatResponse(BaseModel):
    answer: str
    trace: ChatTrace
    task: dict[str, Any] | None = None
    entity: dict[str, Any] | None = None
