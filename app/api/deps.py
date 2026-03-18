from collections.abc import Generator
from datetime import date
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query
from sqlmodel import Session

from app.db.session import get_session


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
