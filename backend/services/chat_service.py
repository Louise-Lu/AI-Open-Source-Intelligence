from __future__ import annotations

from agent.github_agent import github_agent
from agent.trace import clear_trace
from router.entity_extractor import EntityExtractor
from router.entity_resolver import EntityResolver
from router.task_router import TaskRouter
from services.analysis_service import RepositoryAnalysisService
from services.comparison_service import RepositoryComparisonService
from services.profile_service import RepositoryProfileService
from services.roadmap_service import RepositoryRoadmapService


class ChatService:
    def __init__(self):
        self.router = TaskRouter()
        self.entity_extractor = EntityExtractor()
        self.entity_resolver = EntityResolver()
        self.agent = github_agent
        self.profile = RepositoryProfileService()
        self.roadmap = RepositoryRoadmapService()
        self.comparison = RepositoryComparisonService()
        self.analysis_report = RepositoryAnalysisService()

    def chat(self, message: str, owner: str, repo: str) -> dict:
        clear_trace()

        task = self.router.route(message)
        print("task是", task)
        entity = self.entity_extractor.extract(message)
        print("entity是", entity)
        task_dict = task if isinstance(task, dict) else task.model_dump()
        entity_dict = entity if isinstance(entity, dict) else entity.model_dump()

        resolved_entities = self._resolve_entities(entity_dict.get("projects", []))
        resolved_payload = (
            resolved_entities[0]
            if len(resolved_entities) == 1
            else {"projects": resolved_entities}
        )

        route = task_dict.get("route", "agent")

        if route in {"profile", "roadmap", "analysis_report"}:
            resolved = resolved_entities[0] if resolved_entities else None
            if not resolved or not resolved.get("owner") or not resolved.get("repo"):
                return self._not_found_response(task_dict, resolved_payload)
            
            print("task_dict是",task_dict,"resolved_payload是",resolved_payload)

            if route == "profile":
                result = self.profile.generate(resolved["owner"], resolved["repo"])
                print("profile的结果", result)
                return self._wrap_result(result, task_dict, resolved_payload, "summary")

            if route == "roadmap":
                result = self.roadmap.predict(resolved["owner"], resolved["repo"])
                return self._wrap_result(result, task_dict, resolved_payload, "prediction_reasoning")

            result = self.analysis_report.analyze(resolved["owner"], resolved["repo"])
            return self._wrap_result(result, task_dict, resolved_payload, "analysis")

        if route == "comparison":
            if len(resolved_entities) < 2:
                return self._not_found_response(task_dict, resolved_payload)

            left, right = resolved_entities[0], resolved_entities[1]
            if not all([left.get("owner"), left.get("repo"), right.get("owner"), right.get("repo")]):
                return self._not_found_response(task_dict, resolved_payload)

            result = self.comparison.compare(
                left["owner"],
                left["repo"],
                right["owner"],
                right["repo"],
            )
            return self._wrap_result(result, task_dict, resolved_payload, "comparison")

        config = {"recursion_limit": 12}
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        answer = result["messages"][-1].content
        return {
            "answer": answer,
            "trace": {
                "task": task_dict,
                "entity": resolved_payload,
            },
            "task": task_dict,
            "entity": resolved_payload,
        }

    def _resolve_entities(self, projects: list[dict]) -> list[dict]:
        resolved_entities: list[dict] = []
        for project in projects:
            name = project.get("name")
            if not name:
                continue
            resolved_entities.append(self.entity_resolver.resolve(name))
        return resolved_entities

    @staticmethod
    def _not_found_response(task: dict, entity: dict) -> dict:
        return {
            "answer": "没有找到对应的 GitHub 项目，请提供准确仓库地址",
            "trace": {
                "task": task,
                "entity": entity,
            },
            "task": task,
            "entity": entity,
        }
    
    # task: {'route': 'profile'}
    # entity: {'name': 'dify', 'owner': 'langgenius', 'repo': 'dify'}
    # answer_key : summary 
    @staticmethod
    def _wrap_result(result: object, task: dict, entity: dict, answer_key: str) -> dict:
        if hasattr(result, "model_dump"):
            payload = result.model_dump()
        elif isinstance(result, dict):
            payload = dict(result)
        else:
            payload = {"answer": str(result)}

        answer = payload.get("answer") or payload.get(answer_key)
        if not answer:
            answer = str(payload)

        print(answer)
        return {
            "answer": answer,
            "trace": {
                "task": task,
                "entity": entity,
            },
            "task": task,
            "entity": entity,
        }
