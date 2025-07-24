from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.langchain_agent import stream_chat_response_json
from models.schemas import ChatInput, ChatOutput

router = APIRouter()


@router.post("/chat/stream", response_model=ChatOutput)
async def chat_stream_endpoint(chat_input: ChatInput):
    return StreamingResponse(
        stream_chat_response_json(chat_input.prompt),
        media_type="text/event-stream",
    )
