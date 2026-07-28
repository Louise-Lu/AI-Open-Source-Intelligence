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
from .commit import CommitActivityTool
from .discussion import DiscussionTool
from .planning import PlanningTool
from .ecosystem_signal import EcosystemSignalTool
from .utils import build_query, raise_for_github_response

class GitHubClient:
    """用于GitHub API调用的共享HTTP客户端."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None): 
        self.session = requests.Session()
        self.token = token or os.getenv("GITHUB_TOKEN")
        
        # SSL 修复：指定 TLS 版本，避免某些网络环境下的 SSL EOF 错误
        self.session.mount("https://", requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=3,
        ))
        
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Connection": "keep-alive",
            }
        )
        
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

        # 代理配置：从环境变量读取，没有则直连
        proxies = {}
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        no_proxy = os.getenv("NO_PROXY") or os.getenv("no_proxy")
        
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
        if no_proxy:
            proxies["no_proxy"] = no_proxy
        # 强制不走代理（如果环境里有但你想绕过）
        # proxies = {"http": None, "https": None}
        
        if proxies:
            self.session.proxies.update(proxies)

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None
    ) -> requests.Response:
        
        url = f"{self.BASE_URL}{path}"

        merged_headers = self.session.headers.copy()
        if headers:
            merged_headers.update(headers)

        response = self.session.get(
            url,
            params=build_query(params),
            headers=merged_headers,
            timeout=30
        )
        raise_for_github_response(response)
        
        return response
    
# class GitHubClient:
#     """用于GitHub API调用的共享HTTP客户端."""

#     BASE_URL = "https://api.github.com"

#     def __init__(self, token: str | None = None): 
#         self.session = requests.Session()
#         self.token = token or os.getenv("GITHUB_TOKEN")  # ① 从参数或环境变量获取
#         self.session.headers.update(
#             {
#                 "Accept": "application/vnd.github+json",
#                 "X-GitHub-Api-Version": "2022-11-28",
#             }
#         )
#         if self.token:
#             self.session.headers["Authorization"] = f"Bearer {self.token}"  # ② 添加到请求头

    # def get(
    #     self,
    #     path: str,
    #     params: dict[str, Any] | None = None,
    #     headers: dict[str, str] | None = None   # 新增
    # ) -> requests.Response:
        
    #     url = f"{self.BASE_URL}{path}"
    #     # print("GitHub API calling:", url)

    #     # 合并自定义 headers（覆盖默认 headers）
    #     merged_headers = self.session.headers.copy()
    #     if headers:
    #         merged_headers.update(headers)

    #     response = self.session.get(
    #         url,
    #         params=build_query(params),
    #         headers=merged_headers,
    #         timeout=30
    #     )
    #     raise_for_github_response(response)
        
    #     return response


class GitHubAPI(
    RepositoryTool,
    ReadmeTool,
    ReleaseTool,
    IssueTool,
    PullRequestTool,
    # ContributorTool,
    CommitActivityTool,
    PlanningTool,
    DiscussionTool,
    EcosystemSignalTool,
):

    def __init__(self, token: str | None = None, competitor_map: dict[str, list[str]] | None = None):
        self.client = GitHubClient(token=token)
        self.competitor_map = competitor_map or {}  
