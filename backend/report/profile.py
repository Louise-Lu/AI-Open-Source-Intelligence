from pydantic import BaseModel, Field


class RepositoryProfile(BaseModel):
    full_name: str
    description: str | None = None
    language: str | None = None
    license: str | None = None
    stars: int
    forks: int
    topics: list[str]

    maintenance_score: int = Field(ge=0, le=10)
    enterprise_score: int = Field(ge=0, le=10)
    community_score: int = Field(ge=0, le=10)

    summary: str
    recommendation: str
