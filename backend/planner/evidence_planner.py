# from __future__ import annotations

# from schemas.evidence import EvidencePlan
# from schemas.task import TaskRoute


# class EvidencePlanner:
#     def plan(self, task: dict, reports: list[str]) -> dict:
#         task_model = task if isinstance(task, TaskRoute) else TaskRoute.model_validate(task)
#         reports_list = list(reports or [])

#         required_tools: list[str] = []

#         for report in reports_list:
#             required_tools.extend(self._tools_for_report(task_model.task, report))

#         required_tools = self._dedupe(required_tools)
#         print("plan出来需要的tools是",required_tools)
#         return EvidencePlan(required_tools=required_tools).model_dump()

#     @staticmethod
#     def _tools_for_report(task: str, report: str) -> list[str]:
#         if report == "profile":
#             return ["repository", "readme"]
#         if report == "project_health":
#             return ["repository", "issues", "pull_requests", "releases"]
#         if report == "roadmap":
#             return ["repository", "readme", "releases", "issues", "pull_requests"]
#         if report == "comparison":
#             return ["repository", "readme", "releases", "issues", "pull_requests"]
#         if report == "recommendation":
#             return ["repository", "readme", "releases", "issues", "pull_requests"]
#         if report == "release_diff":
#             return ["releases", "repository"]
#         return ["repository", "readme"]

#     @staticmethod
#     def _dedupe(items: list[str]) -> list[str]:
#         seen = set()
#         ordered: list[str] = []
#         for item in items:
#             if item not in seen:
#                 seen.add(item)
#                 ordered.append(item)
#         return ordered
