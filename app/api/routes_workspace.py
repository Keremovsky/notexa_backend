from annotated_types import doc
from fastapi import UploadFile, File, Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session, joinedload
import shutil
import os
from uuid import uuid4
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from models import db_models
from models.db_models import User, Document
from db.session import get_db
from utils.user_utils import get_current_user
from models.schemas import (
    DocumentListOut,
    DocumentOut,
    NoteAdd,
    WorkspaceCreate,
    NoteOut,
    WorkspaceListOut,
    WorkspaceOut,
)

router = APIRouter()

# WORKSPACE


@router.post("")
async def create_workspace(
    workspace_create: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_workspace = db_models.Workspace(
        user_id=current_user.id, name=workspace_create.name
    )

    db.add(db_workspace)
    db.commit()
    db.refresh(db_workspace)

    return {}


@router.get("/all")
async def get_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspaces = (
        db.query(db_models.Workspace)
        .filter(db_models.Workspace.user_id == current_user.id)
        .all()
    )

    return WorkspaceListOut(
        workspaces=[WorkspaceOut.model_validate(workspace) for workspace in workspaces]
    )


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = (
        db.query(db_models.Workspace)
        .options(
            joinedload(db_models.Workspace.document).joinedload(
                db_models.Document.notes
            )
        )
        .filter(db_models.Workspace.id == workspace_id)
        .first()
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return DocumentListOut(
        docs=[
            DocumentOut(
                id=doc.id,
                name=doc.filename,
                notes=[NoteOut(id=note.id, title=note.title) for note in doc.notes],
            )
            for doc in workspace.document
        ],
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = (
        db.query(db_models.Workspace)
        .filter(
            db_models.Workspace.id == workspace_id,
            db_models.Workspace.user_id == current_user.id,
        )
        .first()
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    db.delete(workspace)
    db.commit()


# DOCUMENT


@router.post("/documents/upload/{workspace_id}")
async def upload_document(
    workspace_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = (
        db.query(db_models.Workspace)
        .filter(
            db_models.Workspace.id == workspace_id,
            db_models.Workspace.user_id == current_user.id,
        )
        .first()
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    file_id = str(uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    saved_name = f"{file_id}{file_ext}"
    upload_path = f"uploads/user_{current_user.id}"
    os.makedirs(upload_path, exist_ok=True)

    full_path = os.path.join(upload_path, saved_name)
    with open(full_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Document(
        filename=file.filename, file_path=full_path, workspace_id=workspace.id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"document_id": doc.id}


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


@router.delete("/documents/{document_id}", status_code=HTTP_204_NO_CONTENT)
async def removeDocument(
    document_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db_document = db.query().filter(db_models.Document.id == document_id).first()

    if not db_document:
        raise HTTPException(status_code=404, detail="Document is not found")

    db.delete(db_document)
    db.commit()


# NOTES


@router.post("/notes")
async def add_note(
    note_add: NoteAdd,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_note = db_models.Note(document_id=note_add.doc, title=note_add.title)

    db.add(db_note)
    db.commit()
    db.refresh(db_note)

    return db_note


@router.delete("notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_note(
    note_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_note = db.query().filter(db_models.Note.id == note_id).first()

    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(db_note)
    db.commit()
