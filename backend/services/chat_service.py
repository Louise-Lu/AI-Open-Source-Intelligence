from __future__ import annotations

from agent.github_agent import github_agent
from agent.trace import clear_trace
from router.task_router import TaskRouter
from router.entity_extractor import EntityExtractor
from router.entity_resolver import EntityResolver

from planner.evidence_planner import EvidencePlanner
from evidence.executor.multi_source_evidence import EvidenceExecutor
from sources.github import GitHubAPI
from sources.huggingface import HuggingFaceClient

from services.answer_composer import AnswerComposer

from schemas.entity import ResolvedEntity

# 1. 任务识别 2. 主体识别 3. 系统识别主体 -> sources 
# 4. 根据 task -> features -> 需要的 evidence tools 
# 5. 构建 多源 evidence 6. 根据 evidence -> llm -> composed answer
class ChatService:
    def __init__(self):
        self.router = TaskRouter()
        self.entity_extractor = EntityExtractor()
        self.entity_resolver = EntityResolver()
        self.evidence_planner = EvidencePlanner()

        self.evidence_executor = EvidenceExecutor(
            github_client=GitHubAPI(),
            huggingface_client=HuggingFaceClient(),
            # reddit_client=RedditClient() if os.getenv("REDDIT_ENABLED") else None,
        )
        self.answer_composer = AnswerComposer()
        self.agent = github_agent

    def chat(self, message: str) -> dict:
        clear_trace()

        task = self.router.route(message)
        entity = self.entity_extractor.extract(message)

        task_dict = task if isinstance(task, dict) else task.model_dump()
        entity_dict = entity if isinstance(entity, dict) else entity.model_dump()
        print(task_dict, entity_dict)

        resolved_entities = self._resolve_entities(entity_dict.get("entities", []))
        print("系统识别后的实体的信息源: ",resolved_entities)

        task_type = task_dict.get("task")
        features = task_dict.get("features", [])

        # 若 任务是 general_question，直接调用通用agent对话代理，返回结果
        if task_type == "general_question":
            return self._agent_response(message, task_dict, entity_dict, resolved_entities)

        
        # 若 任务是 比较，则 分别调用 plan 和 构建 evidence
        elif task_type == "project_comparison":
            evidences = []
            for entity in resolved_entities:
                evidence_plan = self.evidence_planner.plan(entity, features)
    
                evidence = self.evidence_executor.collect(entity, evidence_plan)
                evidences.append(evidence)
            
        else:
            evidences = []
            first_entity = resolved_entities[0]
            evidence_plan = self.evidence_planner.plan(first_entity, features)
            evidence = self.evidence_executor.collect(first_entity, evidence_plan)
            evidences.append(evidence)
        
        composed = self.answer_composer.compose(
            message,
            entity_dict,     
            evidences,
        )
        return self._response(task_dict, entity_dict, resolved_entities, composed.answer)


    def _resolve_entities(self, entities: list[dict]) -> list[ResolvedEntity]:
        resolved_entities: list[ResolvedEntity] = []
        for entity in entities:
            resolved = self.entity_resolver.resolve(entity)
            resolved_entities.append(resolved)
        return resolved_entities

    @staticmethod
    def _response(
        task: dict,
        entity: dict,
        resolved_entities: list[dict],
        answer: str,
    ) -> dict:
        return {
            "answer": answer,
            "trace": {
                "task": task,
                "entity": entity,
                "resolved_entities": resolved_entities,
            },
        }

    @staticmethod
    def _not_found_response(task: dict, entity: dict) -> dict:
        return {
            "answer": "",
            "error": "无法确定项目，请提供 GitHub 地址",
            "trace": {
                "task": task,
                "entity": entity,
                "resolved_entities": [],
            },
            "task": task,
            "entity": entity,
            "resolved_entities": [],
        }

    def _agent_response(
        self,
        message: str,
        task: dict,
        entity: dict,
        resolved_entities: list[dict],
    ) -> dict:
        config = {"recursion_limit": 12}
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        answer = result["messages"][-1].content
        return {
            "answer": answer,
            "trace": {
                "task": task,
                "entity": entity,
                "resolved_entities": resolved_entities,
            },
            # "task": task,
            # "entity": entity,
            # "resolved_entities": resolved_entities,
        }
