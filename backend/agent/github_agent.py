# ReAct： 思考 行动 观察 -> 循环
from langgraph.prebuilt import create_react_agent

# from llms.qwen import qwen_model
from llms.deepseek import deepseek_model

from prompts.chat import CHAT_PROMPT
# from prompts.system import SYSTEM_PROMPT
from agent.tools import TOOLS


github_agent = create_react_agent(
    model=deepseek_model,
    tools=TOOLS,
    prompt=CHAT_PROMPT,
)