from services.evidence_service import RepositoryEvidenceService

from llms.qwen import qwen_model
from prompts.roadmap import ROADMAP_PROMPT

from schemas.roadmap import RoadmapReport



class RepositoryRoadmapService:


    def __init__(self):

        self.evidence_service = (
            RepositoryEvidenceService()
        )



    def predict(
        self,
        owner:str,
        repo:str
    ) -> RoadmapReport:


        # ① Evidence

        evidence = self.evidence_service.collect(
            owner,
            repo
        )


        # ② structured output

        llm = qwen_model.with_structured_output(
            RoadmapReport
        )


        # ③ Prompt

        prompt=f"""
{ROADMAP_PROMPT}


Repository Evidence:

{evidence.model_dump_json(indent=2)}

"""


        # ④ LLM

        # roadmap = llm.invoke(
        #     prompt
        # )


        # return roadmap


        try:
            roadmap = llm.invoke(prompt)

            print("==========  DEBUG ==========")
            print(roadmap)
            print(type(roadmap))
            print("===================================")

            return roadmap

        except Exception as e:
                print("========== roadmap ERROR ==========")
                print(e)
                print("===================================")
                raise