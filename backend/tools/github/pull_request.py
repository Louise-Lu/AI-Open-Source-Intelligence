from __future__ import annotations

from typing import Any

from .utils import normalize_list


class PullRequestTool:
    """Pull request helper methods."""

    client: Any

    def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        response = self.client.get(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": per_page, "page": page},
        )
        return normalize_list(response.json())

    def get_pull_request(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        response = self.client.get(f"/repos/{owner}/{repo}/pulls/{number}")
        return response.json()

