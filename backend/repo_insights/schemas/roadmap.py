from pydantic import BaseModel, Field, field_validator


class RoadmapReport(BaseModel):

    current_stage: str = "信息不足"

    recent_direction: list[str] = Field(
        default_factory=list
    )

    future_3_months: list[str] = Field(
        default_factory=list
    )

    future_6_12_months: list[str] = Field(
        default_factory=list
    )

    opportunities: list[str] = Field(
        default_factory=list
    )

    risks: list[str] = Field(
        default_factory=list
    )

    prediction_reasoning: str = "信息不足"

    @field_validator(
        "recent_direction",
        "future_3_months",
        "future_6_12_months",
        "opportunities",
        "risks",
        mode="before",
    )
    @classmethod
    def _coerce_str_to_list(cls, v):
        """LLM 可能返回字符串而非数组，兜底转为单元素列表。"""
        if isinstance(v, str):
            return [v]
        return v