from __future__ import annotations

from agent.github_agent import github_agent
from agent.trace import clear_trace
from router.entity_extractor import EntityExtractor
from router.entity_resolver import EntityResolver
from router.task_router import TaskRouter
from services.report_composer import ReportComposer
from services.report_orchestrator import ReportOrchestrator
from schemas.entity import ResolvedEntity

# 1. 任务识别 2. 主体识别 3. 主体解析搜索链接 4. 报告生成 5. 整合报告信息 + query 输出 
class ChatService:
    def __init__(self):
        self.router = TaskRouter()
        self.entity_extractor = EntityExtractor()
        self.entity_resolver = EntityResolver()
        self.report_orchestrator = ReportOrchestrator()
        self.report_composer = ReportComposer()
        self.agent = github_agent

    def chat(self, message: str) -> dict:
        clear_trace()

        task = self.router.route(message)
        print(task)
        entity = self.entity_extractor.extract(message)
        print(entity)

        task_dict = task if isinstance(task, dict) else task.model_dump()
        entity_dict = entity if isinstance(entity, dict) else entity.model_dump()

        resolved_entities = self._resolve_entities(entity_dict.get("entities", []))
        # print(resolved_entities)

        # [ResolvedEntity(name='qwen', 
        # sources=
        # [EntitySource(source='github', identifier='QwenLM/Qwen'), 
        #  EntitySource(source='huggingface', identifier='Qwen/Qwen2.5-7B')])]

        route = task_dict.get("task", "general_question")
        reports = task_dict.get("reports", [])
        # {'task': 'single_project_analysis', 'reports': ['profile', 'analysis']

        if route == "general_question":
            return self._agent_response(message, task_dict, entity_dict, resolved_entities)

        if task_dict.get("need_entity_resolution", False) and not resolved_entities:
            return self._not_found_response(task_dict, entity_dict)

        if route == "project_comparison":
            if len(resolved_entities) < 2:
                return self._not_found_response(task_dict, entity_dict)
            structured_reports = self.report_orchestrator.generate_comparison(
                resolved_entities[0],
                resolved_entities[1],
                reports,
            )
            project_name = f"{resolved_entities[0]['name']} vs {resolved_entities[1]['name']}"
            composed = self.report_composer.compose(project_name, structured_reports)
            return self._response(task_dict, entity_dict, resolved_entities, structured_reports, composed.answer)

        if route in {"single_project_analysis", "update_tracking"}:
            resolved_entity = resolved_entities[0] if resolved_entities else None
            if not resolved_entity:
                return self._not_found_response(task_dict, entity_dict)

            # name='qwen' sources=[EntitySource(source='github', identifier='QwenLM/Qwen'), 
            # EntitySource(source='huggingface', identifier='Qwen/Qwen2.5-7B')]
            structured_reports = self.report_orchestrator.generate_single_project(
                resolved_entity,
                reports,
            )
            
            composed = self.report_composer.compose(
                message,
                resolved_entity.name,     
                structured_reports
            )
            # {'task': 'single_project_analysis', 'reports': ['roadmap'], 'need_entity_resolution': True, 'confidence': 0.9} 
            # {'entities': [{'name': 'LangGraph'}]}
            # [{'name': 'LangGraph', 'owner': 'langchain-ai', 'repo': 'langgraph'}] 
            return self._response(task_dict, entity_dict, resolved_entities, composed.answer)

        if route == "project_search":
            return {
                "answer": "已识别项目名称，可以继续解析为 GitHub 仓库。",
                "trace": {
                    "task": task_dict,
                    "entity": entity_dict,
                    "resolved_entities": resolved_entities,
                },
                "task": task_dict,
                "entity": entity_dict,
                "resolved_entities": resolved_entities,
            }

        return self._agent_response(message, task_dict, entity_dict, resolved_entities)

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
        print(answer)
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
