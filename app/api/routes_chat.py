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


@router.get("/{component_id}")
async def get_chat(
    component_id: int,
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
        .filter(filter_field == component_id)
        .filter(db_models.ChatHistory.chat_mode == mode)
        .first()
    )

    if not db_chat:
        new_chat_kwargs = {"chat_mode": mode, f"{tp}_id": component_id}
        db_chat = db_models.ChatHistory(**new_chat_kwargs)
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)

    return {
        "messages": [
            ChatOutput(sender=m["sender"], text=m["text"])
            for m in (db_chat.messages or [])
        ]
    }


@router.post("/stream")
async def chat_stream_endpoint(
    chat_input: ChatInput,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tp = chat_input.tp
    id_ = chat_input.id
    mode = chat_input.mode

    if tp not in ("document", "note"):
        raise HTTPException(status_code=400, detail="Invalid type")

    filter_field = (
        db_models.ChatHistory.document_id
        if tp == "document"
        else db_models.ChatHistory.note_id
    )

    db_chat = (
        db.query(db_models.ChatHistory)
        .filter(filter_field == id_)
        .filter(db_models.ChatHistory.chat_mode == mode)
        .first()
    )

    if not db_chat:
        db_chat = db_models.ChatHistory(
            messages=[], chat_mode=mode, **{f"{tp}_id": id_}
        )
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)

    full_response_tokens = []

    def collect_token(token: str):
        full_response_tokens.append(token)

    # Create stream generator with token collector
    stream_gen = stream_chat_response_json(chat_input.prompt, on_token=collect_token)

    async def wrapped_stream():
        async for chunk in stream_gen:
            yield chunk

        # Save both messages after stream ends
        db_chat.messages.append({"sender": "user", "text": chat_input.prompt})
        db_chat.messages.append(
            {"sender": "ai", "text": " ".join(full_response_tokens)}
        )
        db.add(db_chat)
        db.commit()

    return StreamingResponse(wrapped_stream(), media_type="text/event-stream")


@router.delete("/clear/{component_id}")
async def clear_chat_history(
    component_id: int,
    tp: str,
    mode: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if tp not in ("document", "note"):
        raise HTTPException(status_code=400, detail="Invalid component type")

    filter_field = (
        db_models.ChatHistory.document_id
        if tp == "document"
        else db_models.ChatHistory.note_id
    )

    chat = (
        db.query(db_models.ChatHistory)
        .filter(filter_field == component_id)
        .filter(db_models.ChatHistory.chat_mode == mode)
        .first()
    )

    if not chat:
        raise HTTPException(status_code=404, detail="Chat history not found")

    chat.messages = []
    db.commit()

    return {"detail": "Chat history cleared"}
