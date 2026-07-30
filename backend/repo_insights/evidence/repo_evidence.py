from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from types import SimpleNamespace

from repo_insights.schemas.entity import RepositoryRef
from evidence.builder import EvidenceBuilder
from sources.github.client import GitHubAPI

# Future 缓存：key = owner/repo, value = (timestamp, Future)
# 第一个请求立即占位 Future，后续并发请求共享同一个 Future，避免重复收集
_cache: dict[str, tuple[float, Future]] = {}
_CACHE_TTL = 300  # 5 分钟
_cache_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=6)


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

        # 快速路径：缓存命中且未过期，直接返回结果
        with _cache_lock:
            cached = _cache.get(cache_key)
            if cached and (time.time() - cached[0]) < _CACHE_TTL:
                future = cached[1]
                if future.done():
                    print(f"[证据收集] 命中缓存: {cache_key}")
                    return future.result()

                # 收集仍在进行中，等待结果（不重复发起）
                print(f"[证据收集] 等待进行中的收集: {cache_key}")
                return future.result()

            # 缓存未命中或已过期，创建 Future 占位
            future = Future()
            _cache[cache_key] = (time.time(), future)

        # 在锁外执行实际收集，避免阻塞其他请求
        try:
            evidence = self._do_collect(owner, repo, cache_key)
            future.set_result(evidence)
            return evidence
        except Exception as exc:
            future.set_exception(exc)
            # 收集失败，清除缓存占位，允许下次重试
            with _cache_lock:
                _cache.pop(cache_key, None)
            raise

    def _do_collect(self, owner: str, repo: str, cache_key: str):
        """实际执行 9 维并发证据收集。"""
        print(f"[证据收集] 开始并发获取: {cache_key}")
        t0 = time.perf_counter()

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
        futures = {
            name: _executor.submit(fn, *args, **kwargs)
            for name, fn, args, kwargs in tasks
        }

        for name, fut in futures.items():
            try:
                results[name] = fut.result()
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
