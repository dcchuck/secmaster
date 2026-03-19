import hashlib
from collections.abc import Generator
from datetime import date
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query
from sqlmodel import Session, select

from app.auth import verify_clerk_token
from app.db.session import get_session
from app.models.user import ApiKey, User


def get_db() -> Generator[Session, None, None]:
    yield from get_session()


def get_as_of(as_of: date | None = Query(default=None, description="Point-in-time date (YYYY-MM-DD)")) -> date | None:
    return as_of


class CursorPagination:
    def __init__(
        self,
        cursor: UUID | None = Query(default=None, description="Cursor for pagination (UUID of last item)"),
        limit: int = Query(default=50, ge=1, le=200, description="Items per page"),
    ):
        self.cursor = cursor
        self.limit = limit


def get_current_user(
    session: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> User:
    """Resolve the current user from Clerk JWT or API key.

    On first authenticated request, auto-creates a User record.
    """
    if x_api_key:
        return _resolve_api_key_user(session, x_api_key)
    if authorization:
        return _resolve_jwt_user(session, authorization)
    raise HTTPException(status_code=401, detail="Authentication required")


def _resolve_jwt_user(session: Session, authorization: str) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        payload = verify_clerk_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    clerk_user_id = payload["sub"]
    user = session.exec(
        select(User).where(User.clerk_user_id == clerk_user_id)
    ).first()
    if not user:
        user = User(
            clerk_user_id=clerk_user_id,
            email=payload.get("email", ""),
            tier="free",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _resolve_api_key_user(session: Session, api_key: str) -> User:
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    db_key = session.exec(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    ).first()
    if not db_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    user = session.get(User, db_key.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
