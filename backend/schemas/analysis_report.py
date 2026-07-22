from pydantic import BaseModel, Field


class RepositoryAnalysisReport(BaseModel):
    project_positioning: str = Field(default="信息不足")
    core_capabilities: list[str] = Field(default_factory=list)
    architecture: list[str] = Field(default_factory=list)
    community_activity: str = Field(default="信息不足")
    enterprise_readiness: str = Field(default="信息不足")
    risks: list[str] = Field(default_factory=list)
    recommended_reasons: list[str] = Field(default_factory=list)
