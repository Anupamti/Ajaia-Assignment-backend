import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.converters import ALLOWED_TAGS
from app.db import get_db
from app.models import Document, DocumentShare, DocumentVersion, User
from app.schemas import (
    DocumentCreate,
    DocumentDetail,
    DocumentListItem,
    DocumentUpdate,
    ShareRequest,
    UserOut,
)

import bleach

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Snapshotting on every autosaved keystroke would flood the table, so a new
# version is only checkpointed if the previous one is older than this.
VERSION_SNAPSHOT_INTERVAL = datetime.timedelta(minutes=5)


def get_accessible_document(document_id: int, user: User, db: Session) -> Document:
    doc = (
        db.query(Document)
        .options(joinedload(Document.shares).joinedload(DocumentShare.shared_with))
        .filter(Document.id == document_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    is_owner = doc.owner_id == user.id
    is_shared = any(s.shared_with_user_id == user.id for s in doc.shares)
    if not (is_owner or is_shared):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return doc


def maybe_snapshot_version(doc: Document, user: User, db: Session, force: bool = False) -> None:
    """Checkpoint the document's current (pre-edit) state as a version.

    Autosaves are gated by VERSION_SNAPSHOT_INTERVAL so continuous typing
    doesn't flood the table; explicit actions like restore should pass
    force=True so the pre-action state is never lost.
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    if not force:
        last_version = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.created_at.desc())
            .first()
        )
        last_created_at = last_version.created_at if last_version is not None else None
        if last_created_at is not None and last_created_at.tzinfo is None:
            # SQLite (used in tests) drops tzinfo on read-back; CockroachDB doesn't.
            last_created_at = last_created_at.replace(tzinfo=datetime.timezone.utc)
        if last_created_at is not None and now - last_created_at < VERSION_SNAPSHOT_INTERVAL:
            return

    db.add(
        DocumentVersion(
            document_id=doc.id,
            title=doc.title,
            content_html=doc.content_html,
            edited_by_id=user.id,
            created_at=now,
        )
    )


def to_detail(doc: Document, user: User) -> DocumentDetail:
    return DocumentDetail(
        id=doc.id,
        title=doc.title,
        content_html=doc.content_html,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        is_owner=doc.owner_id == user.id,
        owner_name=doc.owner.name,
        shared_with=[UserOut(id=s.shared_with.id, name=s.shared_with.name) for s in doc.shares],
    )


@router.get("", response_model=list[DocumentListItem])
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned = db.query(Document).filter(Document.owner_id == user.id).all()
    shared = (
        db.query(Document)
        .join(DocumentShare, DocumentShare.document_id == Document.id)
        .filter(DocumentShare.shared_with_user_id == user.id)
        .all()
    )

    items = [
        DocumentListItem(
            id=d.id, title=d.title, updated_at=d.updated_at, is_owner=True, owner_name=d.owner.name
        )
        for d in owned
    ] + [
        DocumentListItem(
            id=d.id, title=d.title, updated_at=d.updated_at, is_owner=False, owner_name=d.owner.name
        )
        for d in shared
    ]
    items.sort(key=lambda i: i.updated_at, reverse=True)
    return items


@router.post("", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    doc = Document(owner_id=user.id, title=payload.title, content_html="<p></p>")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return to_detail(doc, user)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    doc = get_accessible_document(document_id, user, db)
    return to_detail(doc, user)


@router.patch("/{document_id}", response_model=DocumentDetail)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_accessible_document(document_id, user, db)

    new_title = doc.title
    if payload.title is not None:
        new_title = payload.title.strip()
        if not new_title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title cannot be empty")

    new_content = doc.content_html
    if payload.content_html is not None:
        new_content = bleach.clean(payload.content_html, tags=ALLOWED_TAGS, attributes={}, strip=True)

    if new_title != doc.title or new_content != doc.content_html:
        maybe_snapshot_version(doc, user, db)
        doc.title = new_title
        doc.content_html = new_content

    db.commit()
    db.refresh(doc)
    return to_detail(doc, user)


@router.post("/{document_id}/share", response_model=DocumentDetail)
def share_document(
    document_id: int,
    payload: ShareRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_accessible_document(document_id, user, db)
    if doc.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can share")

    try:
        target_id = int(payload.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id")

    target = db.get(User, target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share with yourself")

    already = db.query(DocumentShare).filter(
        DocumentShare.document_id == doc.id, DocumentShare.shared_with_user_id == target.id
    ).first()
    if already is None:
        db.add(DocumentShare(document_id=doc.id, shared_with_user_id=target.id))
        db.commit()
        db.refresh(doc)

    return to_detail(doc, user)
