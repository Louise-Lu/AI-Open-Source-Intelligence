from __future__ import annotations

from dataclasses import dataclass

from .client import RedditClient


@dataclass
class RedditSource:
    client: RedditClient

    def search_posts(self, query: str, limit: int = 5) -> list[str]:
        return self.client.search_posts(query=query, limit=limit)
