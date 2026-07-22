from pydantic import BaseModel, Field


class ProjectEntity(BaseModel):
    name: str


class EntityExtraction(BaseModel):
    projects: list[ProjectEntity] = Field(default_factory=list)


class ResolvedProjectEntity(BaseModel):
    name: str
    owner: str | None = None
    repo: str | None = None
