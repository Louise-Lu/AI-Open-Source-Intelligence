from __future__ import annotations
from tools.github.client import GitHubAPI
from evidence.builder import EvidenceBuilder

from llms.qwen import qwen_model

from prompts.profile import PROFILE_PROMPT

from report.profile import RepositoryProfile


class RepositoryProfileService:

    def __init__(self):
        self.github = GitHubAPI()
        self.builder = EvidenceBuilder()

    def generate(self, owner: str, repo: str):

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

        # ③ llm
        llm = qwen_model.with_structured_output(
            RepositoryProfile
        )

        profile = llm.invoke(
            PROFILE_PROMPT
            + "\n\n"
            + evidence.model_dump_json(indent=2)
        )

        return profile