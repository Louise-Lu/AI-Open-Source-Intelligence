from __future__ import annotations

"""Repository analysis 编排 service."""

from agent.graph import agent
from evidence import EvidenceBuilder
from tools.github.client import GitHubAPI


class RepositoryAnalysisService:
    """Fetch GitHub data, build evidence, and run the LangGraph agent."""

    def __init__(self) -> None:
        self.github = GitHubAPI()
        self.builder = EvidenceBuilder()

    def analyze(self, owner: str, repo: str) -> str:
        """Run one repository analysis and return the final agent message."""
        # ① 调 GitHub
        repository = self.github.get_repository(owner, repo)
        readme = self.github.get_readme(owner, repo)
        releases = self.github.get_release(owner, repo)
        issues = self.github.list_issues(owner=owner, repo=repo)
        pull_requests = self.github.list_pull_requests(owner=owner, repo=repo)

        # ② Builder 清洗，聚合，整理数据 
        evidence = self.builder.build(
            repository=repository,
            readme=readme,
            releases=releases,
            issues=issues,
            pull_requests=pull_requests,
        )

         # ③ Agent
        result = agent.invoke(
            {
                "messages": [
                    (
                        "user",
                        f"""
请分析下面 GitHub Repository。

{evidence.model_dump_json(indent=2)}
""",
                    )
                ]
            }
        )

        return result["messages"][-1].content

# React
# ↓
# POST /repositories/analyze
# ↓
# api/repository.py
# ↓
# RepositoryAnalysisService
# ↓
# GitHubAPI
# ├── get_repository()
# ├── get_readme()
# ├── get_releases()
# ├── get_issues()
# └── get_pull_requests()

# ↓

# EvidenceBuilder.build() = GitHubEvidence
# ↓
# LangGraph Agent
# ↓
# RepositoryIntelligenceReport
# ↓
# JSON
# ↓
# React