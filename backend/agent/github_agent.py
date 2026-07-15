# ReAct： 思考 行动 观察 -> 循环
from langgraph.prebuilt import create_react_agent

from llms.qwen import qwen_model
from prompts.chat import SYSTEM_PROMPT
from agent.tools import TOOLS

github_agent = create_react_agent(
    model=qwen_model,
    tools=TOOLS,
    prompt=SYSTEM_PROMPT,
)