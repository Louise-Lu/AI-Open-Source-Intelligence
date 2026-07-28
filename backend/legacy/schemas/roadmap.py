from pydantic import BaseModel, Field


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