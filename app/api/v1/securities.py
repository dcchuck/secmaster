from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import CursorPagination, get_as_of, get_db
from app.models.corporate_action import CorporateAction, CorporateActionRead
from app.models.security import (
    Security,
    SecurityIdentifierHistory,
    SecurityIdentifierHistoryRead,
    SecurityRead,
)
from app.models.shares_outstanding import (
    SharesOutstandingHistory,
    SharesOutstandingHistoryRead,
)
from app.services.point_in_time import apply_as_of_filter

router = APIRouter(prefix="/securities", tags=["securities"])


@router.get("", response_model=dict)
def list_securities(
    session: Session = Depends(get_db),
    pagination: CursorPagination = Depends(),
    issuer_id: UUID | None = Query(default=None),
    ticker: str | None = Query(default=None),
    cusip: str | None = Query(default=None),
    as_of: date | None = Depends(get_as_of),
):
    stmt = select(Security)
    if issuer_id:
        stmt = stmt.where(Security.issuer_id == issuer_id)
    if ticker or cusip:
        stmt = stmt.join(
            SecurityIdentifierHistory,
            Security.security_id == SecurityIdentifierHistory.security_id,
        )
        if ticker:
            stmt = stmt.where(SecurityIdentifierHistory.id_type == "ticker")
            stmt = stmt.where(SecurityIdentifierHistory.id_value == ticker)
        if cusip:
            stmt = stmt.where(SecurityIdentifierHistory.id_type == "cusip")
            stmt = stmt.where(SecurityIdentifierHistory.id_value == cusip)
        if as_of:
            stmt = apply_as_of_filter(stmt, SecurityIdentifierHistory, as_of)
    if pagination.cursor:
        stmt = stmt.where(Security.security_id > pagination.cursor)
    stmt = stmt.order_by(Security.security_id).limit(pagination.limit)

    securities = session.exec(stmt).all()
    next_cursor = str(securities[-1].security_id) if len(securities) == pagination.limit else None
    return {
        "items": [SecurityRead.model_validate(s) for s in securities],
        "next_cursor": next_cursor,
    }


@router.get("/{security_id}", response_model=SecurityRead)
def get_security(security_id: UUID, session: Session = Depends(get_db)):
    security = session.get(Security, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")
    return security


@router.get("/{security_id}/identifiers", response_model=list[SecurityIdentifierHistoryRead])
def get_security_identifiers(
    security_id: UUID,
    session: Session = Depends(get_db),
    as_of: date | None = Depends(get_as_of),
):
    security = session.get(Security, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")

    stmt = select(SecurityIdentifierHistory).where(
        SecurityIdentifierHistory.security_id == security_id
    )
    stmt = apply_as_of_filter(stmt, SecurityIdentifierHistory, as_of)
    stmt = stmt.order_by(SecurityIdentifierHistory.effective_start_date)
    return session.exec(stmt).all()


@router.get("/{security_id}/actions", response_model=list[CorporateActionRead])
def get_security_actions(
    security_id: UUID,
    session: Session = Depends(get_db),
):
    security = session.get(Security, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")

    stmt = (
        select(CorporateAction)
        .where(CorporateAction.security_id == security_id)
        .order_by(CorporateAction.effective_date)
    )
    return session.exec(stmt).all()


@router.get("/{security_id}/shares-outstanding", response_model=list[SharesOutstandingHistoryRead])
def get_security_shares_outstanding(
    security_id: UUID,
    session: Session = Depends(get_db),
):
    security = session.get(Security, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")

    stmt = (
        select(SharesOutstandingHistory)
        .where(SharesOutstandingHistory.security_id == security_id)
        .order_by(SharesOutstandingHistory.as_of_date)
    )
    return session.exec(stmt).all()
