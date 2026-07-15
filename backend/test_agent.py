from backend.agent.github_agent import github_agent
result = github_agent.invoke(
    {
        "messages": [
            (
                "user",
                """
langchain-ai/langgraph 最近有什么 release？
"""
            )
        ]
    },
    config={
        "recursion_limit":10
    }
)


print(result["messages"][-1].content)