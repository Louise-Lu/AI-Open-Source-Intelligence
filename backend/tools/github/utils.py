from __future__ import annotations

import base64
from typing import Any, Callable

import requests


class GitHubAPIError(Exception):
    """Raised when GitHub returns a non-success response."""


def decode_base64_content(content: str) -> str:
    """Decode GitHub's base64 encoded blob content."""
    return base64.b64decode(content).decode("utf-8")


def raise_for_github_response(response: requests.Response) -> None:
    """Turn a GitHub response into a readable exception."""
    if response.status_code < 400:
        return

    try:
        payload = response.json()
        message = payload.get("message", response.text)
    except ValueError:
        message = response.text

    raise GitHubAPIError(f"GitHub API Error {response.status_code}: {message}")


def normalize_list(payload: Any) -> list[dict[str, Any]]:
    """GitHub list endpoints normally return a list, but we guard the shape."""
    if isinstance(payload, list):
        return payload
    return []


def build_query(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Remove None values so requests only sends meaningful filters."""
    if not params:
        return {}
    return {key: value for key, value in params.items() if value is not None}


def paginate_items(
    fetch_page: Callable[..., Any], *, per_page: int = 100
) -> list[dict[str, Any]]:
    """Collect all items from a paginated GitHub endpoint."""
    items: list[dict[str, Any]] = []
    page = 1

    while True:
        batch = normalize_list(fetch_page(page=page, per_page=per_page))
        if not batch:
            break

        items.extend(batch)
        if len(batch) < per_page:
            break
        page += 1

    return items
