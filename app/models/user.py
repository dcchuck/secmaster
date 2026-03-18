from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserBase(SQLModel):
    clerk_user_id: str = Field(unique=True, index=True)
    email: str
    tier: str = "free"


class User(UserBase, table=True):
    user_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class UserRead(UserBase):
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class ApiKeyBase(SQLModel):
    label: str | None = None


class ApiKey(ApiKeyBase, table=True):
    __tablename__ = "api_key"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.user_id")
    key_hash: str
    created_at: datetime = Field(default_factory=_utcnow)
    last_used_at: datetime | None = None
    is_active: bool = True


class ApiKeyCreate(SQLModel):
    label: str | None = None


class ApiKeyRead(SQLModel):
    id: UUID
    label: str | None
    created_at: datetime
    last_used_at: datetime | None
    is_active: bool
