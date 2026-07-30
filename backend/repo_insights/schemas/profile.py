from pydantic import BaseModel, Field, field_validator


class EnterpriseReadiness(BaseModel):

    level: str = "信息不足"

    explanation: str = "信息不足"


class RepositoryProfile(BaseModel):

    project_type: str = "信息不足"

    target_users: list[str] = Field(
        default_factory=list
    )

    core_features: list[str] = Field(
        default_factory=list
    )

    technical_stack: list[str] = Field(
        default_factory=list
    )

    strengths: list[str] = Field(
        default_factory=list
    )

    weaknesses: list[str] = Field(
        default_factory=list
    )

    enterprise_readiness: EnterpriseReadiness

    summary: str = ""

    @field_validator(
        "target_users",
        "core_features",
        "technical_stack",
        "strengths",
        "weaknesses",
        mode="before",
    )
    @classmethod
    def _coerce_str_to_list(cls, v):
        """LLM 可能返回字符串而非数组，兜底转为单元素列表。"""
        if isinstance(v, str):
            return [v]
        return v