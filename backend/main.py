from fastapi import FastAPI
from api.routes import router

from fastapi.middleware.cors import CORSMiddleware

# 创建应用实例：这个 app 对象会处理所有进来的 HTTP 请求
app = FastAPI(title="GitHub Intelligence Agent")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许前端域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 所有 API 都放在 api/routes.py
app.include_router(router)

