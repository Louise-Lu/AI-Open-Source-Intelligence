from __future__ import annotations

from shared_schemas.entity import ExtractedEntity, ResolvedEntity


class EntityAdapter:
    def from_owner_repo(self, owner: str, repo: str) -> ResolvedEntity:
        return ResolvedEntity(
            name=f"{owner}/{repo}",
            entity_type="project",
            aliases=[repo, f"{owner}/{repo}"],
            official_name=f"{owner}/{repo}",
        )

    def from_extracted(self, entity: ExtractedEntity) -> ResolvedEntity:
        from backend.research_agent.entity_resolver import EntityResolver

        return EntityResolver().resolve(entity)
