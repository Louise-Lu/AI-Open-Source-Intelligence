from services.evidence_service import RepositoryEvidenceService

# from llms.qwen import qwen_model
from llms.deepseek import deepseek_model
from prompts.analysis import ANALYSIS_PROMPT
# from tools.github.utils import GitHubAPIError

class RepositoryAnalysisService:

    def __init__(self) -> None:

        self.evidence_service = RepositoryEvidenceService()

    def analyze(self, owner: str, repo: str) -> str:

        evidence = self.evidence_service.collect(
            owner,
            repo
        )

        prompt = f"""
{ANALYSIS_PROMPT}
Evidence:
{evidence.model_dump_json(indent=2)}
"""
        # response = qwen_model.invoke(prompt)
        response = deepseek_model.invoke(prompt)
        return response.content
    ## 直接返回 字符串 markdown 


# React
# ↓
# GET /repositories/${owner}/${repo}/analysis
# ↓
# 后端API
# ↓
# api/analysis.py -> analyze_repository()
# ↓
# services/analysis_service.py -> RepositoryAnalysisService.analyze(owner, repo)
# ↓

# 调用 GitHubAPI 封装的TOOLS
# ├── get_repository()
# ├── get_readme()
# ├── get_releases()
# ├── get_issues()
# └── get_pull_requests()
#  ......
  
# ↓ 真实数据
# 
# EvidenceBuilder.build() -> GitHubEvidence 结构化证据
# ↓

# LLM
# ↓

# Markdown - string
# ↓

# React
