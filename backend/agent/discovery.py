from __future__ import annotations

from pydantic import BaseModel, Field


class DiscoveryResult(BaseModel):
    """Discovery Tool 的统一返回结构。"""

    source: str = Field(description="资源来源，例如 github / huggingface / community / web / youtube")
    identifier: str = Field(description="资源标识，例如 owner/repo、model_id、post_id 或 url")
    title: str = Field(default="", description="资源标题")
    url: str = Field(default="", description="资源 URL")
    score: float = Field(default=0.0, description="相关性或排序分数")
    reason: str = Field(default="", description="为什么这个资源与研究目标相关")


def discovery_result(
    *,
    source: str,
    identifier: str,
    title: str = "",
    url: str = "",
    score: float = 0.0,
    reason: str = "",
) -> dict:
    return DiscoveryResult(
        source=source,
        identifier=identifier,
        title=title,
        url=url,
        score=score,
        reason=reason,
    ).model_dump()
