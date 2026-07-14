# tests/test_evidence_builder.py
# 现在可以使用相对导入
from backend.evidence.builder import EvidenceBuilder

git_builder = EvidenceBuilder()

repository = {
    "full_name": "langchain-ai/langgraph",
    "description": "Build stateful AI agents",
    "language": "Python",
    "stargazers_count": 65000,
    "forks_count": 6000,
    "topics": ["agent", "llm"],
    "license": {"name": "MIT"},
}

readme = "# LangGraph\n\nAgent framework"
# 打点调用 build方法
evidence = git_builder.build(
    repository=repository,
    readme=readme,
)

# print(evidence)
# GitHubEvidence(
#     repository=RepositoryInfo(
#         full_name="langchain-ai/langgraph",
#         stars=65000,
#         ...
#     ),
#     readme="# LangGraph...",
#     releases=[],
#     issues=[],
#     pull_requests=[]
# )
print(type(evidence))
print(type(evidence.repository))
print(evidence.repository.full_name)
print(evidence.repository.stars)
print(evidence.repository.language)