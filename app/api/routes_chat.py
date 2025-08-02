from fastapi import APIRouter, Depends, HTTPException
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from langchain_core.messages import HumanMessage, AIMessage

import asyncio
import json

from models import db_models
from services.langchain_agent import initialize_chain
from models.schemas import ChatInput, ChatOutput
from models.db_models import User
from utils.user_utils import get_current_user
from db.session import get_db
from utils.chat_utils import load_context, get_or_create_chat_history

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


@router.websocket("/stream")
async def websocket_chat(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    await websocket.accept()

    try:
        # Parse initial input
        init_data = await websocket.receive_text()
        chat_input = ChatInput(**json.loads(init_data))

        if chat_input.tp not in ("document", "note"):
            await websocket.send_json({"error": "Invalid type"})
            await websocket.close()
            return

        db_chat = get_or_create_chat_history(db, chat_input)

        doc_texts, note_texts, error = await load_context(chat_input, db)
        if error:
            await websocket.send_json({"error": error})
            await websocket.close()
            return

        conversation, memory = initialize_chain(db_chat)

        while True:
            user_input = await websocket.receive_text()
            memory.chat_memory.add_message(HumanMessage(content=user_input))
            full_tokens = []

            async for chunk in conversation.llm.astream(memory.chat_memory.messages):
                token = chunk.content
                full_tokens.append(token)
                await websocket.send_text(token)
                await asyncio.sleep(0)

            ai_response = "".join(full_tokens)
            memory.chat_memory.add_message(AIMessage(content=ai_response))

            db_chat.messages.extend(
                [
                    {"sender": "user", "text": user_input},
                    {"sender": "ai", "text": ai_response},
                ]
            )
            db.add(db_chat)
            db.commit()

    except WebSocketDisconnect:
        print("WebSocket disconnected")

    except Exception as e:
        await websocket.send_text(json.dumps({"error": str(e)}))
        await websocket.close()


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
