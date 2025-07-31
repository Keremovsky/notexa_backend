from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models import db_models
from services.langchain_agent import stream_chat_response_json
from models.schemas import ChatInput, ChatOutput
from models.db_models import User
from utils.user_utils import get_current_user
from db.session import get_db

router = APIRouter()


@router.get("/{id}")
async def get_chat(
    id: int,
    tp: str,
    mode: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if tp not in ("document", "note"):
        raise HTTPException(401, detail="Mode is not valid")

    filter_field = (
        db_models.ChatHistory.document_id
        if tp == "document"
        else db_models.ChatHistory.note_id
    )

    db_chat = (
        db.query(db_models.ChatHistory)
        .filter(filter_field == id)
        .filter(db_models.ChatHistory.chat_mode == mode)
        .first()
    )

    if not db_chat:
        new_chat_kwargs = {"chat_mode": mode, f"{tp}_id": id}
        db_chat = db_models.ChatHistory(**new_chat_kwargs)
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)

    return {
        "messages": [
            ChatOutput(sender=m.sender, answer=m.answer)
            for m in (db_chat.messages or [])
        ]
    }


@router.post("/stream", response_model=ChatOutput)
async def chat_stream_endpoint(
    chat_input: ChatInput,
    _: User = Depends(get_current_user),
):
    return StreamingResponse(
        stream_chat_response_json(chat_input.prompt),
        media_type="text/event-stream",
    )
