from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.session import Base
from enum import Enum as PyEnum


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    token = relationship("RefreshToken", back_populates="user", uselist=False)
    workspace = relationship("Workspace", back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="token")


class Workspace(Base):
    __tablename__ = "workspace"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="workspace")
    document = relationship("Document", back_populates="workspace")


class ChatModeEnum(PyEnum):
    role = "role"
    tutor = "tutor"
    chat = "chat"


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)

    # Structured messages: [{"sender": "user"|"ai", "text": "..."}]
    messages = Column(JSON, nullable=False)

    chat_mode = Column(Enum(ChatModeEnum), nullable=False, index=True)

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"))
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="SET NULL"))

    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    document = relationship("Document", back_populates="chat")
    note = relationship("Note", back_populates="chat")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)  # e.g., "myfile.pdf"
    file_path = Column(String, nullable=False)  # e.g., "/uploads/user_123/myfile.pdf"
    upload_time = Column(DateTime, default=datetime.now(timezone.utc))

    workspace_id = Column(Integer, ForeignKey("workspace.id", ondelete="CASCADE"))

    chat = relationship("ChatHistory", back_populates="document", uselist=False)
    workspace = relationship("Workspace", back_populates="document")
    notes = relationship("Note", back_populates="document")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, default="")
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))

    document = relationship("Document", back_populates="notes")
    chat = relationship("ChatHistory", back_populates="note", uselist=False)
