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
        repository = self.github.get_repository(owner, repo)
        readme = self.github.get_readme(owner, repo)
        releases = self.github.get_release(owner, repo)
        issues = self.github.list_issues(owner=owner, repo=repo)

        evidence = self.builder.build(
            repository=repository,
            readme=readme,
            releases=releases,
            issues=issues,
        )

        llm = qwen_model.with_structured_output(RepositoryProfile)

        repository_info = evidence.repository
        if repository_info is None:
            raise ValueError("Repository evidence is required to build a profile")

        release_titles = [
            release.tag_name
            for release in evidence.releases[:3]
            if release.tag_name
        ]
        issue_titles = [issue.title for issue in evidence.issues[:5] if issue.title]
        readme_excerpt = (evidence.readme or "")[:2000]
        release_titles_block = (
            "\n".join(f"- {title}" for title in release_titles) if release_titles else "- None"
        )
        issue_titles_block = (
            "\n".join(f"- {title}" for title in issue_titles) if issue_titles else "- None"
        )

        prompt = (
            f"{PROFILE_PROMPT.strip()}\n\n"
            "Repository:\n"
            f"- full_name: {repository_info.full_name}\n"
            f"- description: {repository_info.description}\n"
            f"- language: {repository_info.language}\n"
            f"- license: {repository_info.license}\n"
            f"- stars: {repository_info.stars}\n"
            f"- forks: {repository_info.forks}\n"
            f"- topics: {repository_info.topics}\n\n"
            "Recent Releases:\n"
            f"{release_titles_block}\n\n"
            "Recent Issues:\n"
            f"{issue_titles_block}\n\n"
            "README:\n"
            f"{readme_excerpt}"
        )

        profile = llm.invoke(prompt)

        return profile
