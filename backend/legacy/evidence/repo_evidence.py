from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from legacy.schemas.entity import RepositoryRef
from evidence.builder import EvidenceBuilder
from sources.github.client import GitHubAPI

# 简单内存缓存：key = owner/repo, value = (timestamp, evidence)
_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 300  # 5 分钟


class RepositoryEvidenceService:
    def __init__(self):
        self.github = GitHubAPI()
        self.builder = EvidenceBuilder()

    def collect(
        self,
        entity: RepositoryRef | str | None = None
    ):
        if isinstance(entity, str):
            raise ValueError("Entity-based collection expects a RepositoryRef")

        if entity is None:
            raise ValueError("Entity is required")

        github_source = self._get_source(entity, "github")
        if not github_source:
            return self.builder.build()

        owner, repo = self._split_github_identifier(github_source.identifier)
        cache_key = f"{owner}/{repo}"

        # 检查缓存
        cached = _cache.get(cache_key)
        if cached and (time.time() - cached[0]) < _CACHE_TTL:
            print(f"[证据收集] 命中缓存: {cache_key}")
            return cached[1]

        print(f"[证据收集] 开始并发获取: {cache_key}")
        t0 = time.perf_counter()

        # 9 个调用互相独立，并发执行
        def _call(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        tasks = [
            ("repository", self.github.get_repository, (owner, repo), {}),
            ("readme", self.github.get_readme, (owner, repo), {}),
            ("releases", self.github.get_releases, (owner, repo), {}),
            ("issues", self.github.get_issues, (), {"owner": owner, "repo": repo}),
            ("pull_requests", self.github.get_pull_requests, (), {"owner": owner, "repo": repo}),
            ("commit_activity", self.github.get_commit_activity, (owner, repo), {}),
            ("planning", self.github.get_planning_signals, (owner, repo), {}),
            ("discussions", self.github.get_discussion_signals, (owner, repo), {}),
            ("ecosystem", self.github.get_ecosystem_signals, (owner, repo), {}),
        ]

        results = {}
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                name: pool.submit(_call, fn, *args, **kwargs)
                for name, fn, args, kwargs in tasks
            }

            for name, future in futures.items():
                try:
                    results[name] = future.result()
                except Exception as exc:
                    print(f"[证据收集] {name} 失败: {exc}")
                    results[name] = None

        elapsed = time.perf_counter() - t0
        print(f"[证据收集] 并发完成: {cache_key}, 耗时={elapsed:.2f}s")

        evidence = self.builder.build(
            repository=results.get("repository"),
            readme=results.get("readme"),
            releases=results.get("releases"),
            issues=results.get("issues"),
            pull_requests=results.get("pull_requests"),
            commit_activity=results.get("commit_activity"),
            planning=results.get("planning"),
            discussions=results.get("discussions"),
            ecosystem=results.get("ecosystem"),
        )

        # 写入缓存
        _cache[cache_key] = (time.time(), evidence)
        return evidence

    @staticmethod
    def _get_source(entity: RepositoryRef, source_name: str):
        sources = getattr(entity, "sources", None)
        if sources:
            for source in sources:
                if source.source == source_name:
                    return source

        if source_name != "github":
            return None

        candidates = [
            getattr(entity, "name", None),
            *list(getattr(entity, "aliases", []) or []),
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and "/" in candidate:
                return SimpleNamespace(source="github", identifier=candidate)
        return None

    @staticmethod
    def _split_github_identifier(identifier: str) -> tuple[str, str]:
        if "/" not in identifier:
            raise ValueError(f"Invalid GitHub identifier: {identifier}")
        return identifier.split("/", 1)
