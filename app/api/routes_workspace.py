from fastapi import UploadFile, File, Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
import shutil
import os
from uuid import uuid4
from typing import List

from models.db_models import User, Document
from db.session import get_db
from utils.user_utils import get_current_user
from models.schemas import DocumentOut

router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_id = str(uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    saved_name = f"{file_id}{file_ext}"
    upload_path = f"uploads/user_{current_user.id}"
    os.makedirs(upload_path, exist_ok=True)

    full_path = os.path.join(upload_path, saved_name)
    with open(full_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Document(filename=file.filename, file_path=full_path, user_id=current_user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"document_id": doc.id}


@router.get("/documents", response_model=List[DocumentOut])
def get_user_documents(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    documents = db.query(Document).filter(Document.user_id == current_user.id).all()
    if not documents:
        raise HTTPException(status_code=404, detail="No documents found for user")
    return documents


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document_by_id(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this document"
        )

    return document


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this document"
        )

    file_path = document.file_path
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    file_like = open(file_path, mode="rb")
    return StreamingResponse(file_like, media_type="application/pdf")
