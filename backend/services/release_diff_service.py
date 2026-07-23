from llms.deepseek import deepseek_model
from prompts.release_diff import RELEASE_DIFF_PROMPT
from schemas.release_diff import ReleaseDiffEvidence


class ReleaseDiffService:
    def compare(self, evidence: ReleaseDiffEvidence) -> str:
        response = deepseek_model.invoke(
            RELEASE_DIFF_PROMPT + "\n\n" + evidence.model_dump_json(indent=2)
        )
        return response.content
