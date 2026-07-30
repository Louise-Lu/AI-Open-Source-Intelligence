from __future__ import annotations

from repo_insights.schemas.entity import RepositoryRef


class EntityAdapter:
    def from_owner_repo(self, owner: str, repo: str) -> RepositoryRef:
        return RepositoryRef(
            name=f"{owner}/{repo}",
            aliases=[repo],
        )

    def from_name(self, name: str) -> RepositoryRef:
        return RepositoryRef(name=name.strip())
