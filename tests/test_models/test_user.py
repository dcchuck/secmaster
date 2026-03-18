import hashlib
from datetime import datetime
from uuid import UUID

from app.models.user import ApiKey, User


def test_create_user(session):
    user = User(
        clerk_user_id="user_abc123",
        email="test@example.com",
        tier="free",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    assert isinstance(user.user_id, UUID)
    assert user.clerk_user_id == "user_abc123"
    assert user.tier == "free"


def test_create_api_key(session):
    user = User(clerk_user_id="user_xyz", email="paid@example.com", tier="paid")
    session.add(user)
    session.commit()

    key_hash = hashlib.sha256(b"test-api-key").hexdigest()
    api_key = ApiKey(
        user_id=user.user_id,
        key_hash=key_hash,
        label="My Test Key",
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)

    assert isinstance(api_key.id, UUID)
    assert api_key.key_hash == key_hash
    assert api_key.is_active is True
