import json
import traceback

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from research_agent.schemas.chat import ChatRequest, ChatResponse, ChatTrace
from research_agent.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])
service = ChatService()


@router.post("", response_model=ChatResponse)
async def chat(request: Request):
    body = await request.json()
    payload = ChatRequest.model_validate(body)

    try:
        result = service.chat(message=payload.message)
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return JSONResponse(
            status_code=200,
            content={
                "answer": f"研究服务内部出错：{type(exc).__name__}: {exc}",
                "trace": {},
                "error": str(exc),
            },
        )

    if hasattr(result, "model_dump"):
        result = result.model_dump()

    # 安全提取字段，防止 result 为 None 或缺少键
    answer = result.get("answer", "") if isinstance(result, dict) else ""
    error = result.get("error") if isinstance(result, dict) else None
    trace_data = result.get("trace", {}) if isinstance(result, dict) else {}

    # 确保 trace 是可序列化的 dict
    if not isinstance(trace_data, dict):
        trace_data = {"raw": str(trace_data)[:2000]}

    # 最终 JSON 序列化校验 — 如果失败，降级为最小响应
    try:
        json.dumps(trace_data, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        trace_data = {"serialization_error": str(exc)[:500]}

    return ChatResponse(
        answer=answer,
        trace=ChatTrace(**trace_data) if trace_data else ChatTrace(),
        error=error,
    )
