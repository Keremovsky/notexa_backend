from pydantic import BaseModel, EmailStr
from typing import List


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    username: str
    email: EmailStr
    refresh: str
    access: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class ChatInput(BaseModel):
    prompt: str


class ChatOutput(BaseModel):
    sender: str
    answer: str


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class WorkspaceListOut(BaseModel):
    workspaces: List[WorkspaceOut]


class NoteAdd(BaseModel):
    doc: int
    title: str


class NoteOut(BaseModel):
    id: int
    title: str


class DocumentOut(BaseModel):
    id: int
    name: str
    notes: List[NoteOut]


class DocumentListOut(BaseModel):
    docs: List[DocumentOut]
