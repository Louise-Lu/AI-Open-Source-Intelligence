from __future__ import annotations

from typing import Any

from .utils import normalize_list


class ReleaseTool:
    """Release helper."""

    client: Any

    def get_release(self, owner: str, repo: str) -> list[dict[str, Any]]:
        # GitHub exposes releases at `/releases`, not `/release`.
        response = self.client.get(f"/repos/{owner}/{repo}/releases")
        return normalize_list(response.json())

