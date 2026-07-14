from evidence.models import RepositoryInfo
from pydantic import BaseModel, Field


class RepositoryProfile(BaseModel):
    repository: RepositoryInfo

    maintenance_score: int = Field(ge=0, le=10)
    enterprise_score: int = Field(ge=0, le=10)
    community_score: int = Field(ge=0, le=10)

    summary: str
    recommendation: str