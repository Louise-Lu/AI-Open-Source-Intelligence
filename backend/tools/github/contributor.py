from __future__ import annotations

from typing import Any

from .utils import normalize_list


class ContributorTool:
    """Contributor helper methods."""

    client: Any

    def list_contributors(
        self,
        owner: str,
        repo: str,
        anon: bool = False,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        response = self.client.get(
            f"/repos/{owner}/{repo}/contributors",
            params={"anon": str(anon).lower(), "per_page": per_page, "page": page},
        )
        return normalize_list(response.json())

