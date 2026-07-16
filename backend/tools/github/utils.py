from __future__ import annotations

import base64
from typing import Any, Callable

import requests


class GitHubAPIError(Exception):
    """Raised when GitHub returns a non-success response."""
    def __init__(self, status_code: int, message: str, details: dict[str, Any] | None = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(message)


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
        status_code=response.status_code,
        message=message,
        details=details
    ) 