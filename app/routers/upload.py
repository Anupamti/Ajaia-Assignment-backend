from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.converters import file_to_html, is_supported_filename
from app.db import get_db
from app.models import Document, User
from app.routers.documents import to_detail
from app.schemas import DocumentDetail

router = APIRouter(prefix="/api/documents", tags=["upload"])


@router.post("/upload", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not is_supported_filename(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt and .md files are supported",
        )

    raw = await file.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large")
    if not raw.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")

    content_html = file_to_html(file.filename, raw)
    title = file.filename.rsplit(".", 1)[0][:255] or "Untitled document"

    doc = Document(owner_id=user.id, title=title, content_html=content_html)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return to_detail(doc, user)
