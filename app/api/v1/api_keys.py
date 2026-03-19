import hashlib
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_db
from app.models.user import ApiKey, ApiKeyCreate, ApiKeyRead, User

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", status_code=201)
def create_api_key(
    body: ApiKeyCreate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.tier != "paid":
        raise HTTPException(status_code=403, detail="API keys require paid tier")

    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        user_id=current_user.user_id,
        key_hash=key_hash,
        label=body.label,
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)

    return {
        "id": str(api_key.id),
        "key": raw_key,  # only returned on creation
        "label": api_key.label,
        "created_at": api_key.created_at.isoformat(),
    }


@router.get("", response_model=list[ApiKeyRead])
def list_api_keys(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ApiKey).where(
        ApiKey.user_id == current_user.user_id,
        ApiKey.is_active == True,
    )
    return session.exec(stmt).all()


@router.delete("/{key_id}", status_code=204)
def delete_api_key(
    key_id: UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = session.get(ApiKey, key_id)
    if not api_key or api_key.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    session.add(api_key)
    session.commit()
