from services.evidence_service import RepositoryEvidenceService

# from llms.qwen import qwen_model
from llms.deepseek import deepseek_model
from prompts.profile import PROFILE_PROMPT

from schemas.profile import RepositoryProfile

class RepositoryProfileService:


    def __init__(self):

        self.evidence_service = (
            RepositoryEvidenceService()
        )


    def generate(
        self,
        owner: str,
        repo: str
    ) -> RepositoryProfile:


        # ① 获取统一 Evidence

        evidence = self.evidence_service.collect(
            owner,
            repo
        )


        # ② structured output

        # llm = qwen_model.with_structured_output(
        #     RepositoryProfile
        # )
        llm = deepseek_model.with_structured_output(
            RepositoryProfile
        )

        # ③ Prompt

        prompt = f"""
{PROFILE_PROMPT}


Repository Evidence:

{evidence.model_dump_json(indent=2)}
"""


        # ④ LLM

        # profile = llm.invoke(
        #     prompt
        # )

        try:
            profile = llm.invoke(prompt)

            print("========== PROFILE DEBUG ==========")
            print(profile)
            print(type(profile))
            print("===================================")

            return profile

        except Exception as e:
            print("========== PROFILE ERROR ==========")
            print(e)
            print("===================================")
            raise
