from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    name: str


class EntityExtraction(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)


class ResolvedEntity(BaseModel):
    name: str
    entity_type: str = Field(
        default="unknown",
        description="实体类型: project | technology | company | model | product | framework | unknown",
    )
    aliases: list[str] = Field(default_factory=list)
    official_name: str | None = None
