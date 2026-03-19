import jwt
import httpx
from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Fetch Clerk JWKS for JWT verification. Cached in-process."""
    if not settings.clerk_jwks_url:
        return {}
    response = httpx.get(settings.clerk_jwks_url)
    response.raise_for_status()
    return response.json()


def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT and return the payload.

    Returns dict with at minimum 'sub' (Clerk user ID).
    Raises jwt.InvalidTokenError on failure.
    """
    jwks = _get_jwks()
    if not jwks:
        raise jwt.InvalidTokenError("JWKS not configured")

    # Get the signing key from JWKS
    header = jwt.get_unverified_header(token)
    key = None
    for jwk in jwks.get("keys", []):
        if jwk["kid"] == header.get("kid"):
            key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
            break

    if key is None:
        raise jwt.InvalidTokenError("Signing key not found in JWKS")

    payload = jwt.decode(token, key, algorithms=["RS256"])
    return payload
