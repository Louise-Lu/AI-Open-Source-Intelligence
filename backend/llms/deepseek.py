import os
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

load_dotenv()

# 创建 DeepSeek 模型实例
# 对于支持工具调用的模型，使用 "deepseek-chat"
deepseek_model = ChatDeepSeek(
    model="deepseek-chat",  # 或你确认支持工具调用的模型名
    temperature=0,
    # max_tokens=None,
    # timeout=None,
    # max_retries=2,
    api_key=os.getenv("DEEPSEEK_API_KEY"), 
)