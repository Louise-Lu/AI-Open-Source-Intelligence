from tools.github.client import GitHubAPI
from evidence import EvidenceBuilder

# 业务：生成 GitHub Evidence : IntelligenceEvidence
# 调用了 builder()
# RepositoryEvidenceService:
# 1. 请求 github api：github tools 
# 2. 构建 structured evidence: IntelligenceEvidence
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
        
        commit_activity = self.github.get_commit_activity(owner, repo)
        planning = self.github.get_planning_signals(owner, repo)
        discussions = self.github.get_discussion_signals(owner, repo)


        # 构建 structured evidence: 类型 IntelligenceEvidence
        evidence = self.builder.build(
            repository=repository,
            readme=readme,
            releases=releases,
            issues=issues,
            pull_requests=pull_requests,
            commit_activity=commit_activity,      
            planning=planning,                    
            discussions=discussions,              
        )

        return evidence