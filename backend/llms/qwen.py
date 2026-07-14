import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

qwen_model = ChatOpenAI(
    model="qwen-max",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)