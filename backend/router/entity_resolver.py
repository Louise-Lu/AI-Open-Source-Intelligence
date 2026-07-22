from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.github.client import GitHubAPI


@dataclass
class ResolvedEntity:
    name: str
    owner: str | None
    repo: str | None

    @property
    def found(self) -> bool:
        return bool(self.owner and self.repo)

    def model_dump(self) -> dict[str, str | None]:
        return {
            "name": self.name,
            "owner": self.owner,
            "repo": self.repo,
        }


class EntityResolver:
    def __init__(self):
        self.github = GitHubAPI()

    def resolve(self, name: str) -> dict[str, str | None]:
        query = name.strip()
        if not query:
            return {"name": "", "owner": None, "repo": None}

        result = self._search_repository(query)
        if result:
            return result

        return {"name": query, "owner": None, "repo": None}

    def _search_repository(self, project_name: str) -> dict[str, str | None] | None:
        response = self.github.client.get(
            "/search/repositories",
            params={
                "q": project_name,
                "per_page": 1,
            },
        )
        payload: dict[str, Any] = response.json()
        items = payload.get("items") or []
        if not items:
            return None

        lowered = project_name.strip().lower()
        first = self._pick_best_item(items, lowered)
        full_name = first.get("full_name") or ""
        owner = (first.get("owner") or {}).get("login")
        repo = first.get("name")

        if not owner or not repo:
            if "/" in full_name:
                owner, repo = full_name.split("/", 1)

        if not owner or not repo:
            return None

        return {
            "name": project_name,
            "owner": owner,
            "repo": repo,
        }

    @staticmethod
    def _pick_best_item(items: list[dict[str, Any]], lowered_query: str) -> dict[str, Any]:
        for item in items:
            name = (item.get("name") or "").lower()
            full_name = (item.get("full_name") or "").lower()
            if name == lowered_query or full_name.endswith(f"/{lowered_query}"):
                return item
        return items[0] or {}
