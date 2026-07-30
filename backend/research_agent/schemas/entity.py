from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    name: str


class EntityExtraction(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)


class ResolvedEntity(BaseModel):
    name: str
    entity_scope: list[str] = Field(
        default_factory=lambda: ["web"],
        description="该实体的信息存在于哪些平台: github | huggingface | web。LLM 推断。",
    )
    entity_origin: str = Field(
        default="unknown",
        description="实体归属: chinese (中国项目) | international (海外项目) | unknown",
    )
    aliases: list[str] = Field(default_factory=list)
    official_name: str | None = None
