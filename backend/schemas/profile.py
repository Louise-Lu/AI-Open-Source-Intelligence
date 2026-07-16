from pydantic import BaseModel, Field

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