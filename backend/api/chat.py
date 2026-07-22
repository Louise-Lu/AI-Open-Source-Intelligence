# 是“Controller（控制器）” 或 “路由层” 的角色，
# 负责接收前端请求、校验数据、调用业务逻辑（ChatService），最后把结果返回给前端

from fastapi import APIRouter, Request

from schemas.chat import ChatRequest, ChatResponse
from services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])
service = ChatService()

# 后端处理前端的request 
# 1.校验前端request的数据格式 2.调用业务逻辑 3.返回给前端
@router.post("", response_model=ChatResponse)
async def chat(request: Request):
    body = await request.json()  # ① 拿到前端的请求：JSON 字符串
    payload = ChatRequest.model_validate(body)  # ③ 校验字段是否存在
    result = service.chat(message=payload.message)

    if hasattr(result, "model_dump"):
        result = result.model_dump()

    return ChatResponse(
        answer=result.get("answer", ""),
        trace=result.get("trace", {}),
        task=result.get("task"),
        entity=result.get("entity"),
        error=result.get("error"),
    )
