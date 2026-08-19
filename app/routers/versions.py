from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.db import get_db
from app.models import DocumentVersion, User
from app.routers.documents import get_accessible_document, maybe_snapshot_version, to_detail
from app.schemas import DocumentDetail, VersionDetail, VersionListItem

router = APIRouter(prefix="/api/documents/{document_id}/versions", tags=["versions"])


def get_version(document_id: int, version_id: int, user: User, db: Session) -> DocumentVersion:
    doc = get_accessible_document(document_id, user, db)
    version = (
        db.query(DocumentVersion)
        .options(joinedload(DocumentVersion.edited_by))
        .filter(DocumentVersion.id == version_id, DocumentVersion.document_id == doc.id)
        .first()
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return version


@router.get("", response_model=list[VersionListItem])
def list_versions(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_accessible_document(document_id, user, db)
    versions = (
        db.query(DocumentVersion)
        .options(joinedload(DocumentVersion.edited_by))
        .filter(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.created_at.desc())
        .all()
    )
    return [
        VersionListItem(
            id=v.id, title=v.title, created_at=v.created_at, edited_by_name=v.edited_by.name
        )
        for v in versions
    ]


@router.get("/{version_id}", response_model=VersionDetail)
def get_version_detail(
    document_id: int,
    version_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    version = get_version(document_id, version_id, user, db)
    return VersionDetail(
        id=version.id,
        title=version.title,
        content_html=version.content_html,
        created_at=version.created_at,
        edited_by_name=version.edited_by.name,
    )


@router.post("/{version_id}/restore", response_model=DocumentDetail)
def restore_version(
    document_id: int,
    version_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    version = get_version(document_id, version_id, user, db)
    doc = version.document

    # Checkpoint the current state first so restoring never loses work.
    maybe_snapshot_version(doc, user, db, force=True)
    doc.title = version.title
    doc.content_html = version.content_html

    db.commit()
    db.refresh(doc)
    return to_detail(doc, user)
