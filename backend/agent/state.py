# # 共享的信息流
# from typing import TypedDict, Optional

# # 以后所有 Node 都操作这个 State。
# class AgentState(TypedDict):

#     repo_url: str

#     owner: str

#     repo: str

#     user_goal: str

#     repository: Optional[dict]

#     readme: Optional[str]

#     releases: Optional[list]

#     issues: Optional[list]

#     pull_requests: Optional[list]

#     contributors: Optional[list]

#     report: Optional[str]