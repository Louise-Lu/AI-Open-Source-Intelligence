from evidence import IntelligenceEvidence
from llms.deepseek import deepseek_model
from legacy.prompts.comparison import COMPARISON_PROMPT
from legacy.schemas.comparison import RepositoryComparisonReport


class RepositoryComparisonService:
    def compare(
        self,
        left_evidence: IntelligenceEvidence,
        right_evidence: IntelligenceEvidence,
    ) -> RepositoryComparisonReport:
        prompt = f"""
{COMPARISON_PROMPT}

Repository A

{left_evidence.model_dump_json(indent=2)}

Repository B

{right_evidence.model_dump_json(indent=2)}
"""
        response = deepseek_model.invoke(prompt)
        return RepositoryComparisonReport(comparison=response.content)
