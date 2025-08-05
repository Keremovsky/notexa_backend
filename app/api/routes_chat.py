from fastapi import APIRouter, Depends, HTTPException
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

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


embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


@router.websocket("/stream")
async def websocket_chat(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    await websocket.accept()

    try:
        init_data = await websocket.receive_text()
        chat_input = ChatInput(**json.loads(init_data))

        if chat_input.tp not in ("document", "note"):
            await websocket.send_json({"error": "Invalid type"})
            await websocket.close()
            return

        db_chat = get_or_create_chat_history(db, chat_input)

        conversation, memory = initialize_chain(db_chat, chat_input.mode)

        while True:
            user_input = await websocket.receive_text()

            docs, notes, error = load_context(chat_input, db, user_input)

            full_prompt_messages = []

            if error or not docs:
                await websocket.send_json(
                    {
                        "error": f"Context loading failed: {error or 'No documents found'}"
                    }
                )
                await websocket.close()
                return

            doc_context = "\n\n".join([doc for doc in docs])
            doc_system_message = SystemMessage(
                content=f"Here are some relevant documents:\n{doc_context}"
            )
            full_prompt_messages.append(doc_system_message)

            if notes:
                note_context = "\n\n".join([note for note in notes])
                note_system_message = SystemMessage(
                    content=f"Here are some relevant notes from user:\n{note_context}"
                )
                full_prompt_messages.append(note_system_message)

            messages = memory.chat_memory.messages

            full_prompt_messages.extend(messages)
            full_prompt_messages.append(HumanMessage(content=user_input))

            memory.chat_memory.add_message(HumanMessage(content=user_input))

            full_tokens = []

            async for chunk in conversation.llm.astream(full_prompt_messages):
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
