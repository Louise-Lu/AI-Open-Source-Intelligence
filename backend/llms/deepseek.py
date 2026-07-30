import os
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

load_dotenv()

# 创建 DeepSeek 模型实例
# 对于支持工具调用的模型，使用 "deepseek-chat"
deepseek_model = ChatDeepSeek(
    model="deepseek-v4-pro",
    temperature=0,
    # max_tokens=None,
    # timeout=None,
    # max_retries=2,
    api_key=os.getenv("DEEPSEEK_API_KEY"), 
)

# 关闭思考模式的模型实例 —— 专用于 with_structured_output
# DeepSeek V4 思考模式下禁止 tool_choice 参数，
# 而 with_structured_output 内部会强制设置 tool_choice: "required"，导致 400 错误
deepseek_structured_model = ChatDeepSeek(
    model="deepseek-v4-pro",
    temperature=0,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    extra_body={"thinking": {"type": "disabled"}},
)