# from llms.qwen import qwen_model
from llms.deepseek import deepseek_model
from prompts.comparison import COMPARISON_PROMPT

from schemas.comparison import RepositoryComparisonReport

from services.profile_service import RepositoryProfileService


class RepositoryComparisonService:

    def __init__(self):
        self.profile_service = RepositoryProfileService()

    def analyze(
        self,
        owner1: str,
        repo1: str,
        owner2: str,
        repo2: str,
    ) -> RepositoryComparisonReport:

        profile1 = self.profile_service.generate(
            owner1,
            repo1,
        )

        profile2 = self.profile_service.generate(
            owner2,
            repo2,
        )

        prompt = f"""
{COMPARISON_PROMPT}

Repository A

{profile1.model_dump_json(indent=2)}

Repository B

{profile2.model_dump_json(indent=2)}
"""

        # response = qwen_model.invoke(prompt)
        response = deepseek_model.invoke(prompt)
        return RepositoryComparisonReport(
            comparison=response.content
        )