from __future__ import annotations

from tools.github.client import GitHubAPI
from evidence import EvidenceBuilder

from llms.qwen import qwen_model
from prompts.analysis import ANALYSIS_PROMPT
from tools.github.utils import GitHubAPIError

class RepositoryAnalysisService:

    def __init__(self) -> None:
        self.github = GitHubAPI()
        self.builder = EvidenceBuilder()

    def analyze(self, owner: str, repo: str) -> str:
        """Run one repository analysis and return the final message."""
        # ① 调 GitHub
        try:
            repository = self.github.get_repository(owner, repo)
            readme = self.github.get_readme(owner, repo)
            releases = self.github.get_releases(owner, repo)
            issues = self.github.get_issues(owner=owner, repo=repo)
            pull_requests = self.github.get_pull_requests(owner=owner, repo=repo)

        except GitHubAPIError as e:
            # 可以在这里记录日志
            print(f"GitHub API 调用失败: {e}")
            raise  # 重新抛出，让全局异常处理器处理


        # ② Builder 清洗，聚合，整理数据 
        evidence = self.builder.build(
            repository=repository,
            readme=readme,
            releases=releases,
            issues=issues,
            pull_requests=pull_requests,
        )

        prompt = f"""
{ANALYSIS_PROMPT}
Evidence:
{evidence.model_dump_json(indent=2)}
"""
        response = qwen_model.invoke(prompt)

        return response.content
    ## 直接返回 字符串 markdown 


# React
# ↓
# GET /repositories/analyze
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
# LLM
# ↓
# Markdown - string
# ↓
# React
