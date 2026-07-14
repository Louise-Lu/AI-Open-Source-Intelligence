from fastapi import FastAPI
from api.analysis import router as analysis_router
from api.compare import router as compare_router
from api.profile import router as profile_router
from api.release_diff import router as release_diff_router
from api.routes import router as base_router

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

app.include_router(base_router)
app.include_router(profile_router)
app.include_router(analysis_router)
app.include_router(compare_router)
app.include_router(release_diff_router)
