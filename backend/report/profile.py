from pydantic import BaseModel, ConfigDict, Field


class RepositoryProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str = ""
    description: str | None = None
    language: str | None = None
    license: str | None = None
    stars: int = 0
    forks: int = 0
    topics: list[str] = Field(default_factory=list)

    maintenance_score: int = Field(default=0, ge=0, le=10)
    enterprise_score: int = Field(default=0, ge=0, le=10)
    community_score: int = Field(default=0, ge=0, le=10)

    summary: str = ""
    recommendation: str = ""
