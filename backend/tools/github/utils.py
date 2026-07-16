from __future__ import annotations

import base64
from typing import Any, Callable

import requests


class GitHubAPIError(Exception):
    """Raised when GitHub returns a non-success response."""
    def __init__(self, message: str, status_code: int = None, details: dict[str, Any] = None):
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

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

    details = {}
    
    # 增加更友好的错误信息
    if response.status_code == 404:
        url = response.url
        if "repos" in url:
            parts = url.split("/repos/")[-1].split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                message = f"仓库 {owner}/{repo} 不存在或无法访问"
                details = {"owner": owner, "repo": repo, "suggestion": "请检查仓库名称是否正确"}
            else:
                message = f"资源不存在: {message}"
        else:
            message = f"资源不存在: {message}"
    elif response.status_code == 403:
        if "rate limit" in message.lower():
            message = "GitHub API 速率限制已超出"
            details = {"limit": "rate_limit", "suggestion": "请稍后再试或配置认证令牌"}
        else:
            message = f"访问被拒绝: {message}"
            details = {"suggestion": "请检查是否有权限访问该仓库"}
    elif response.status_code == 401:
        message = f"认证失败: {message}"
        details = {"suggestion": "请检查 GitHub 认证配置"}
    elif response.status_code == 502 or response.status_code == 503:
        message = "GitHub API 暂时不可用"
        details = {"suggestion": "请稍后再试"}

    raise GitHubAPIError(
        message=message,
        status_code=response.status_code,
        details=details
    )

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