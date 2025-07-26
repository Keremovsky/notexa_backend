from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from services.langchain_agent import stream_chat_response_json
from models.schemas import ChatInput, ChatOutput
from models.db_models import User
from utils.user_utils import get_current_user

router = APIRouter()


@router.post("/stream", response_model=ChatOutput)
async def chat_stream_endpoint(
    chat_input: ChatInput,
    _: User = Depends(get_current_user),
):
    return StreamingResponse(
        stream_chat_response_json(chat_input.prompt),
        media_type="text/event-stream",
    )
