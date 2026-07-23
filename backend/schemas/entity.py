from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    name: str


class EntityExtraction(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)


class EntitySource(BaseModel):
    source: str
    identifier: str


class ResolvedEntity(BaseModel):
    name: str
    sources: list[EntitySource] = Field(default_factory=list)
