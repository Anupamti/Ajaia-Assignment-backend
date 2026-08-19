import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

# CockroachDB's default row IDs are 64-bit and can exceed JavaScript's safe
# integer range (2^53), which silently corrupts them if sent as JSON numbers.
# All IDs are therefore serialized as strings, same as Stripe/Twitter/Discord
# do for large IDs.
IdStr = Annotated[str, BeforeValidator(str)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: IdStr
    name: str


class LoginRequest(BaseModel):
    user_id: str


class DocumentCreate(BaseModel):
    title: str = Field(default="Untitled document", max_length=255)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    content_html: str | None = None


class ShareRequest(BaseModel):
    user_id: str


class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user: UserOut


class DocumentListItem(BaseModel):
    id: IdStr
    title: str
    updated_at: datetime.datetime
    is_owner: bool
    owner_name: str


class DocumentDetail(BaseModel):
    id: IdStr
    title: str
    content_html: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_owner: bool
    owner_name: str
    shared_with: list[UserOut]


class VersionListItem(BaseModel):
    id: IdStr
    title: str
    created_at: datetime.datetime
    edited_by_name: str


class VersionDetail(BaseModel):
    id: IdStr
    title: str
    content_html: str
    created_at: datetime.datetime
    edited_by_name: str
