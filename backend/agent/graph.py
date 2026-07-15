# Repository Analysis（ReAct Agent）
# from langgraph.prebuilt import create_react_agent
# from prompts.analysis import ANALYSIS_PROMPT

# # from agent.tools import TOOLS
# from llms.qwen import qwen_model

# # ReAct： 思考 行动 观察 -> 循环
# agent = create_react_agent(
#     model=qwen_model,
#     tools=[],
#     prompt=ANALYSIS_PROMPT,
# )

from langgraph.prebuilt import create_react_agent

from llms.qwen import qwen_model
from prompts.chat import SYSTEM_PROMPT
from agent.tools import TOOLS

agent = create_react_agent(
    model=qwen_model,
    tools=TOOLS,
    prompt=SYSTEM_PROMPT,
)