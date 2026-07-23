from __future__ import annotations

import os
from typing import Any

import requests


class RedditClient:
    BASE_URL = "https://www.reddit.com"
    OAUTH_URL = "https://oauth.reddit.com"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
    ):
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or os.getenv("REDDIT_USER_AGENT") or "ai-intelligence-agent/1.0"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self._access_token: str | None = None

    def _auth_headers(self) -> dict[str, str]:
        if self.client_id and self.client_secret:
            token = self._get_access_token()
            if token:
                return {
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self.user_agent,
                }
        return {"User-Agent": self.user_agent}

    def _get_access_token(self) -> str | None:
        if self._access_token:
            return self._access_token

        if not self.client_id or not self.client_secret:
            return None

        response = self.session.post(
            f"{self.BASE_URL}/api/v1/access_token",
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self.user_agent},
            timeout=30,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        self._access_token = payload.get("access_token")
        return self._access_token

    def search_posts(self, query: str, limit: int = 5) -> list[str]:
        params = {
            "q": query,
            "limit": limit,
            "sort": "relevance",
            "type": "link",
            "restrict_sr": False,
        }

        response = self.session.get(
            f"{self.OAUTH_URL}/search.json" if self.client_id and self.client_secret else f"{self.BASE_URL}/search.json",
            params=params,
            headers=self._auth_headers(),
            timeout=30,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        children = payload.get("data", {}).get("children", [])

        posts: list[str] = []
        for child in children[:limit]:
            data = child.get("data", {})
            title = data.get("title")
            subreddit = data.get("subreddit")
            score = data.get("score")
            if title:
                suffix = f" | r/{subreddit} | score:{score}" if subreddit is not None else ""
                posts.append(f"{title}{suffix}")
        return posts
