import logging

from evidence import IntelligenceEvidence
from llms.deepseek import deepseek_model
from legacy.prompts.profile import PROFILE_PROMPT
from legacy.schemas.profile import RepositoryProfile

logger = logging.getLogger(__name__)


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
            logger.warning("Repository profile generation failed: %s", exc)
            raise
