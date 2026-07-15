from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


from typing import Any


class ChatResponse(BaseModel):

    answer: str

    trace: list[dict[str, Any]] = []