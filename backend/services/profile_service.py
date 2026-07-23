from evidence import IntelligenceEvidence
from llms.deepseek import deepseek_model
from prompts.profile import PROFILE_PROMPT
from schemas.profile import RepositoryProfile


class RepositoryProfileService:
    def generate(self, evidence: IntelligenceEvidence) -> RepositoryProfile:
        llm = deepseek_model.with_structured_output(RepositoryProfile)
        prompt = f"""
{PROFILE_PROMPT}


Repository Evidence:

{evidence.model_dump_json(indent=2)}
"""
        try:
            return llm.invoke(prompt)
        except Exception as exc:
            print("========== PROFILE ERROR ==========")
            print(exc)
            print("===================================")
            raise
