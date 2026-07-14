from langgraph.prebuilt import create_react_agent

from agent.prompts import SYSTEM_PROMPT
# from agent.tools import TOOLS
from llms.qwen import qwen_model

# ReAct： 思考 行动 观察 -> 循环
agent = create_react_agent(
    model=qwen_model,
    tools=[],
    prompt=SYSTEM_PROMPT,
)