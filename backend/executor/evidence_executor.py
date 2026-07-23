# 根据entity和plan，调用具体的 API 客户端收集原始数据，
# 并构建成结构化证据（IntelligenceEvidence）。

from typing import Any
from evidence import EvidenceBuilder
from evidence.models import IntelligenceEvidence
from schemas.entity import ResolvedEntity
from planner.evidence_planner import EvidencePlan

from sources.github.client import GitHubAPI
from sources.huggingface.client import HuggingFaceClient
from sources.reddit.client import RedditClient


# EvidencePlan(required_tools=['github_commit_activity', 'github_issue', 
# 'github_pull_request', 'github_readme', 'github_release', 'github_repository', 
# 'huggingface_model'])

class EvidenceExecutor:
    def __init__(
        self,
        github_client: GitHubAPI,
        huggingface_client: HuggingFaceClient,
        # reddit_client: RedditClient | None = None,
    ):
        self.github = github_client
        self.huggingface = huggingface_client
        # self.reddit = reddit_client
        self.builder = EvidenceBuilder()

    def collect(self, entity: ResolvedEntity, plan: EvidencePlan) -> IntelligenceEvidence:
        """
        根据 Evidence Plan 的 Tools 收集证据，返回结构化 IntelligenceEvidence
        """

        print("=== DEBUG entity ===")
        print(f"type: {type(entity)}")
        print(f"content: {entity}")
        if hasattr(entity, 'sources'):
            print(f"sources: {entity.sources}")
            for s in entity.sources:
                print(f"  - source: {s.source}, identifier: {s.identifier}")
        else:
            print("entity has NO 'sources' attribute")
        print("=====================")


        # 防御：如果 entity 是列表，取第一个
        if isinstance(entity, list):
            if not entity:
                raise ValueError("Entity list is empty")
            entity = entity[0]
            print(f"Warning: entity was a list, using first: {entity}")

        github_raw = None
        huggingface_raw = None
        # reddit_raw = None
    

        # ---------- 收集 GitHub raw data ----------
        github_tools = [t for t in plan.required_tools if t.startswith("github")]
        if github_tools:
            github_source = next((s for s in entity.sources if s.source == "github"), None)
            print("github_source", github_source)
            if github_source:
                try:
                    owner, repo = github_source.identifier.split("/", 1)
                    github_raw = self._collect_github_raw_data(owner, repo, github_tools)
                except Exception as e:
                    print(f"GitHub raw data collection error: {e}")
                    github_raw = None

        # ---------- 收集 HuggingFace raw data ----------
        hf_tools = [t for t in plan.required_tools if t.startswith("huggingface")]
        if hf_tools:
            hf_source = next((s for s in entity.sources if s.source == "huggingface"), None)
            if hf_source:
                try:
                    huggingface_raw = self.huggingface.get_model(hf_source.identifier)
                except Exception as e:
                    print(f"HuggingFace collection error: {e}")
                    huggingface_raw = None

        # # ---------- 收集 Reddit ----------
        # if plan.include_reddit and self.reddit:
        #     # 如果有 github 信息，用它作为查询关键词；否则尝试用实体名称
        #     try:
        #         query = entity.name
        #         if github_raw and github_raw.get("github_repository"):
        #             query = github_raw["github_repository"].get("full_name") or entity.name
        #         posts = self.reddit.search_posts(query=query, limit=5)
        #         reddit_raw = {
        #             "posts": posts,
        #             "mentions": len(posts),
        #             "sentiment": None,
        #         }
        #     except Exception as e:
        #         print(f"Reddit collection error: {e}")
        #         reddit_raw = None

        # ---------- 构建证据 ----------
        return self.builder.build(
            repository=github_raw.get("github_repository") if github_raw else None,
            readme=github_raw.get("github_readme") if github_raw else None,
            releases=github_raw.get("github_release") if github_raw else None,
            issues=github_raw.get("github_issue") if github_raw else None,
            pull_requests=github_raw.get("github_pull_request") if github_raw else None,
            commit_activity=github_raw.get("github_commit_activity") if github_raw else None,
            planning=github_raw.get("github_planning") if github_raw else None,
            discussions=github_raw.get("github_discussion") if github_raw else None,
            huggingface=huggingface_raw,
            # reddit=reddit_raw,
        )

    def _collect_github_raw_data(self, owner: str, repo: str, tools: list[str]) -> dict[str, Any]:
        """调用 GitHubAPI 的各个工具方法，返回原始数据字典"""
        result = {}
        for tool in tools:
            try:
                if tool == "github_repository":
                    result[tool] = self.github.get_repository(owner, repo)
                    print()
                elif tool == "github_readme":
                    result[tool] = self.github.get_readme(owner, repo)
                elif tool == "github_release":
                    result[tool] = self.github.get_releases(owner, repo)
                elif tool == "github_issue":
                    result[tool] = self.github.get_issues(owner, repo)
                elif tool == "github_pull_request":
                    result[tool] = self.github.get_pull_requests(owner, repo)
                elif tool == "github_commit_activity":
                    result[tool] = self.github.get_commit_activity(owner, repo)
                elif tool == "github_planning":
                    result[tool] = self.github.get_planning_signals(owner, repo)
                elif tool == "github_discussion":
                    result[tool] = self.github.get_discussion_signals(owner, repo)
                else:
                    result[tool] = None
            except Exception as e:
                print(f"GitHub tool {tool} failed: {e}")
                result[tool] = None
        return result