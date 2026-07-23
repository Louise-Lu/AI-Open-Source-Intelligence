from __future__ import annotations

from schemas.entity import EntitySource, ExtractedEntity, ResolvedEntity


class EntityAdapter:
    def from_owner_repo(self, owner: str, repo: str) -> ResolvedEntity:
        return ResolvedEntity(
            name=f"{owner}/{repo}",
            sources=[EntitySource(source="github", identifier=f"{owner}/{repo}")],
        )

    def from_extracted(self, entity: ExtractedEntity) -> ResolvedEntity:
        from router.entity_resolver import EntityResolver

        return EntityResolver().resolve(entity)
