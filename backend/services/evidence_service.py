from tools.github.client import GitHubAPI
from evidence import EvidenceBuilder


class RepositoryEvidenceService:

    def __init__(self):

        self.github = GitHubAPI()
        self.builder = EvidenceBuilder()


    def collect(
        self,
        owner: str,
        repo: str
    ):

        repository = self.github.get_repository(
            owner,
            repo
        )

        readme = self.github.get_readme(
            owner,
            repo
        )

        releases = self.github.get_releases(
            owner,
            repo
        )

        issues = self.github.get_issues(
            owner=owner,
            repo=repo
        )

        pull_requests = self.github.get_pull_requests(
            owner=owner,
            repo=repo
        )


        evidence = self.builder.build(
            repository=repository,
            readme=readme,
            releases=releases,
            issues=issues,
            pull_requests=pull_requests,
        )

        return evidence