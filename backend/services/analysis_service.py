from evidence import IntelligenceEvidence
from llms.deepseek import deepseek_model
from prompts.analysis import ANALYSIS_PROMPT


class RepositoryAnalysisService:
    def analyze(self, evidence: IntelligenceEvidence) -> str:
        prompt = f"""
{ANALYSIS_PROMPT}
Evidence:
{evidence.model_dump_json(indent=2)}
"""
        response = deepseek_model.invoke(prompt)
        return response.content
