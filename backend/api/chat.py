from fastapi import APIRouter

from schemas.chat import (
    ChatRequest,
    ChatResponse
)

from services.chat_service import ChatService



router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


service = ChatService()



@router.post(
    "",
    response_model=ChatResponse
)
def chat(
    request: ChatRequest
):

    result = service.chat(
        request.message
    )


    return ChatResponse(
        answer=result["answer"],
        trace=result["trace"]
    )