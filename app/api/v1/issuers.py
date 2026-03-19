from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import CursorPagination, get_as_of, get_current_user, get_db
from app.models.user import User
from app.models.issuer import (
    Issuer,
    IssuerNameHistory,
    IssuerNameHistoryRead,
    IssuerRead,
)
from app.models.classification import (
    IssuerClassificationHistory,
    IssuerClassificationHistoryRead,
)
from app.services.point_in_time import apply_as_of_filter

router = APIRouter(prefix="/issuers", tags=["issuers"])


@router.get("", response_model=dict)
def list_issuers(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: CursorPagination = Depends(),
    name: str | None = Query(default=None),
    country: str | None = Query(default=None),
):
    stmt = select(Issuer)
    if name:
        stmt = stmt.where(Issuer.legal_name.ilike(f"{name}%"))  # type: ignore
    if country:
        stmt = stmt.where(Issuer.country_incorporation == country)
    if pagination.cursor:
        stmt = stmt.where(Issuer.issuer_id > pagination.cursor)
    stmt = stmt.order_by(Issuer.issuer_id).limit(pagination.limit)

    issuers = session.exec(stmt).all()
    next_cursor = str(issuers[-1].issuer_id) if len(issuers) == pagination.limit else None
    return {
        "items": [IssuerRead.model_validate(i) for i in issuers],
        "next_cursor": next_cursor,
    }


@router.get("/{issuer_id}", response_model=IssuerRead)
def get_issuer(issuer_id: UUID, session: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    issuer = session.get(Issuer, issuer_id)
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")
    return issuer


@router.get("/{issuer_id}/history", response_model=dict)
def get_issuer_history(
    issuer_id: UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    as_of: date | None = Depends(get_as_of),
):
    issuer = session.get(Issuer, issuer_id)
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")

    # Name history
    name_stmt = select(IssuerNameHistory).where(
        IssuerNameHistory.issuer_id == issuer_id
    )
    name_stmt = apply_as_of_filter(name_stmt, IssuerNameHistory, as_of)
    name_stmt = name_stmt.order_by(IssuerNameHistory.effective_start_date)
    name_history = session.exec(name_stmt).all()

    # Classification history
    class_stmt = select(IssuerClassificationHistory).where(
        IssuerClassificationHistory.issuer_id == issuer_id
    )
    class_stmt = apply_as_of_filter(class_stmt, IssuerClassificationHistory, as_of)
    class_stmt = class_stmt.order_by(IssuerClassificationHistory.effective_start_date)
    classification_history = session.exec(class_stmt).all()

    return {
        "issuer": IssuerRead.model_validate(issuer),
        "name_history": [IssuerNameHistoryRead.model_validate(n) for n in name_history],
        "classification_history": [
            IssuerClassificationHistoryRead.model_validate(c) for c in classification_history
        ],
    }
