from __future__ import annotations

from typing import Any

from .utils import decode_base64_content


class ReadmeTool:
    """README helper."""

    client: Any

    def get_readme(self, owner: str, repo: str) -> str:
        response = self.client.get(f"/repos/{owner}/{repo}/readme")
        payload = response.json()
        return decode_base64_content(payload["content"])

