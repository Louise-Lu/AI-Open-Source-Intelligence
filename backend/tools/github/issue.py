from __future__ import annotations

from typing import Any

from .utils import normalize_list


class IssueTool:
    """Issue helper methods."""

    client: Any

    def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        # Keep the method small and predictable for direct API consumption.
        response = self.client.get(
            f"/repos/{owner}/{repo}/issues",
            params={
                "state": state,
                "labels": labels,
                "per_page": per_page,
                "page": page,
            },
        )
        return normalize_list(response.json())

    def get_issue(self, owner: str, repo: str, issue_number: int) -> dict[str, Any]:
        response = self.client.get(f"/repos/{owner}/{repo}/issues/{issue_number}")
        return response.json()

    def list_issue_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        response = self.client.get(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            params={"per_page": per_page, "page": page},
        )
        return normalize_list(response.json())

