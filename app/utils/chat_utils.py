from sqlalchemy.orm import Session
from langchain_community.document_loaders import PyPDFLoader
import os
from models.schemas import ChatInput

from models import db_models


def get_or_create_chat_history(db: Session, chat_input: ChatInput):
    filter_field = (
        db_models.ChatHistory.document_id
        if chat_input.tp == "document"
        else db_models.ChatHistory.note_id
    )

    db_chat = (
        db.query(db_models.ChatHistory)
        .filter(filter_field == chat_input.id)
        .filter(db_models.ChatHistory.chat_mode == chat_input.mode)
        .first()
    )

    if not db_chat:
        db_chat = db_models.ChatHistory(
            messages=[],
            chat_mode=chat_input.mode,
            **{f"{chat_input.tp}_id": chat_input.id},
        )
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)

    return db_chat


async def load_context(chat_input: ChatInput, db: Session):
    doc_texts, note_texts = [], []

    try:
        if chat_input.tp == "document":
            doc = db.query(db_models.Document).filter_by(id=chat_input.id).first()
            if not doc or not os.path.exists(doc.file_path):
                return [], [], "Document not found or file missing"

            loader = PyPDFLoader(doc.file_path)
            async for page in loader.alazy_load():
                doc_texts.append(page.page_content)

            notes = db.query(db_models.Note).filter_by(document_id=doc.id).all()
            if not notes:
                return doc_texts, [], None

            note_texts = [n.content for n in notes]

        elif chat_input.tp == "note":
            note = db.query(db_models.Note).filter_by(id=chat_input.id).first()
            if not note:
                return [], [], "Note not found"

            note_texts.append(note.content)

            doc = db.query(db_models.Document).filter_by(id=note.document_id).first()
            if not doc or not os.path.exists(doc.file_path):
                return [], [], "Document not found or file missing"

            loader = PyPDFLoader(doc.file_path)
            async for page in loader.alazy_load():
                doc_texts.append(page.page_content)

    except Exception as e:
        return [], [], f"Failed to load context: {str(e)}"

    return doc_texts, note_texts, None
