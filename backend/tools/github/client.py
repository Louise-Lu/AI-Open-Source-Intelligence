from __future__ import annotations

import os
from typing import Any

import requests
import time

# from .contributor import ContributorTool
from .issue import IssueTool
from .pull_request import PullRequestTool
from .readme import ReadmeTool
from .release import ReleaseTool
from .repository import RepositoryTool
from .utils import build_query, raise_for_github_response


class GitHubClient:
    """用于GitHub API调用的共享HTTP客户端."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None): 
        self.session = requests.Session()
        self.token = token or os.getenv("GITHUB_TOKEN")  # ① 从参数或环境变量获取
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"  # ② 添加到请求头

    # def get(self, path: str, params: dict[str, Any] | None = None) -> requests.Response:
    #     url = f"{self.BASE_URL}{path}"
    #     response = self.session.get(url, params=build_query(params), timeout=30)
    #     raise_for_github_response(response)
    #     return response


    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None
    ) -> requests.Response:

        url = f"{self.BASE_URL}{path}"

        print("GitHub API calling:", url)

        start = time.time()

        response = self.session.get(
            url,
            params=build_query(params),
            timeout=30
        )

        print(
            "GitHub API finished:",
            response.status_code,
            round(time.time()-start, 2),
            "seconds"
        )

        raise_for_github_response(response)

        return response


class GitHubAPI(
    RepositoryTool,
    ReadmeTool,
    ReleaseTool,
    IssueTool,
    PullRequestTool,
    # ContributorTool,
):

    def __init__(self, token: str | None = None):
        self.client = GitHubClient(token=token)

