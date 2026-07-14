from pydantic import BaseModel, Field


class RepositoryIntelligenceReport(BaseModel):
    """
    GitHub Repository Intelligence Report
    """

    project_name: str = Field(
        description="Repository name"
    )

    summary: str = Field(
        description="Short project summary"
    )

    target_users: str = Field(
        description="Who this project is built for"
    )

    core_capabilities: list[str] = Field(
        description="Main capabilities"
    )

    technology_stack: list[str] = Field(
        description="Languages and frameworks"
    )

    maintenance_status: str = Field(
        description="Maintenance activity"
    )

    community_activity: str = Field(
        description="Community engagement"
    )

    enterprise_readiness: str = Field(
        description="Whether suitable for enterprise"
    )

    strengths: list[str] = Field(
        description="Project strengths"
    )

    risks: list[str] = Field(
        description="Potential risks"
    )

    future_direction: list[str] = Field(
        description="Expected roadmap"
    )

    recommendation: str = Field(
        description="Overall recommendation"
    )