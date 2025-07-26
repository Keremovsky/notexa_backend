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

    tokens = relationship("RefreshToken", back_populates="user")
    chats = relationship("ChatHistory", back_populates="user")
    documents = relationship("Document", back_populates="user", cascade="all, delete")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="tokens")


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

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"))

    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="chats")
    document = relationship("Document", back_populates="chats")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)  # e.g., "myfile.pdf"
    file_path = Column(String, nullable=False)  # e.g., "/uploads/user_123/myfile.pdf"
    upload_time = Column(DateTime, default=datetime.now(timezone.utc))

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="documents")
    chats = relationship("ChatHistory", back_populates="document")
