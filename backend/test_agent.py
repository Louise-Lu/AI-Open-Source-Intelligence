from agent.graph import agent

response = agent.invoke(
    {
        "messages": [
            (
                "user",
                "分析 https://github.com/langchain-ai/langgraph"
            )
        ]
    }
)

print(response["messages"][-1].content)