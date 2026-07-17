from tools.github.client import GitHubAPI
from evidence import EvidenceBuilder

# RepositoryEvidenceService:
# 1. 请求 github api：github tools 
# 2. 构建 structured evidence
class RepositoryEvidenceService:

    def __init__(self):

        self.github = GitHubAPI()
        self.builder = EvidenceBuilder()


    def collect(
        self,
        owner: str,
        repo: str
    ):
        
        # 1. 请求调用 github api：github tools 
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
        
        # 构建 structured evidence
        evidence = self.builder.build(
            repository=repository,
            readme=readme,
            releases=releases,
            issues=issues,
            pull_requests=pull_requests,
        )

        return evidence