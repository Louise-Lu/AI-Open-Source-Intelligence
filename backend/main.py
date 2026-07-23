from fastapi import FastAPI, Request

from fastapi.openapi.docs import get_swagger_ui_html

from api.analysis import router as analysis_router
from api.compare import router as compare_router
from api.profile import router as profile_router
from api.release_diff import router as release_diff_router
from api.routes import router as base_router
from api.chat import router as chat_router
from api.roadmap import router as roadmap_router

from fastapi.responses import JSONResponse
from sources.github.utils import GitHubAPIError

from fastapi.middleware.cors import CORSMiddleware

# 创建应用实例：这个 app 对象会处理所有进来的 HTTP 请求
app = FastAPI(title="GitHub Intelligence Agent",docs_url=None, redoc_url=None)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许前端域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 自定义 Swagger UI（/docs）
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,  # 默认为 /openapi.json
        title=f"{app.title} - Swagger UI",
        # 使用国内可用的 CDN（推荐 cdnjs 或 bootcdn）
        swagger_js_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.10.3/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.10.3/swagger-ui.css",
)

app.include_router(base_router)
app.include_router(analysis_router)
app.include_router(profile_router)
app.include_router(compare_router)
app.include_router(release_diff_router)
app.include_router(roadmap_router)

app.include_router(chat_router)


# 处理 GitHub API 错误
@app.exception_handler(GitHubAPIError)
async def github_api_error_handler(request: Request, exc: GitHubAPIError):
    return JSONResponse(
        status_code=exc.status_code or 500,
        content={
            "success": False,
            "error": {
                "type": "GitHubAPIError",
                "status_code": exc.status_code,
                "message": str(exc),  # 使用 str(exc) 获取异常消息
                "details": exc.details,
                "timestamp": "2026-07-16T12:00:00Z"
            }
        }
    )

# 处理一般的 ValueError
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "type": "ValidationError",
                "message": str(exc),
                "timestamp": "2026-07-16T12:00:00Z"
            }
        }
    )

# 处理其他未预期的异常
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "type": "InternalServerError",
                "message": "服务器内部错误，请稍后再试",
                "timestamp": "2026-07-16T12:00:00Z"
            }
        }
    )