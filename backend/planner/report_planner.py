# # ReportPlanner
# # 决定生成哪些报告

# from dataclasses import dataclass, field

# @dataclass
# class ReportPlan:

#     reports:list[str] = field(
#         default_factory=list
#     )


# class ReportPlanner:


#     TASK_REPORT_MAP = {


#         "single_project_analysis":[
#             "profile",
#             "health",
#             "recommendation"
#         ],


#         "project_comparison":[
#             "comparison"
#         ],


#         "project_update":[
#             "release_diff"
#         ],


#         "market_intelligence":[
#             "trend_report"
#         ],


#         "deep_research":[
#             "profile",
#             "health",
#             "roadmap",
#             "recommendation"
#         ],


#         "general_question":[]
#     }



#     def plan(
#         self,
#         task:str
#     )->ReportPlan:


#         reports = self.TASK_REPORT_MAP.get(
#             task,
#             []
#         )


#         return ReportPlan(
#             reports=reports
#         )