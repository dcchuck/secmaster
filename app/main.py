from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

app = FastAPI(
    title="Secmaster API",
    description="OTC/Microcap Security Master Data",
    version="0.1.0",
)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health")
def health_check():
    return {"status": "ok"}


from app.api.v1.issuers import router as issuers_router  # noqa: E402
from app.api.v1.securities import router as securities_router  # noqa: E402
from app.api.v1.listings import router as listings_router  # noqa: E402
from app.api.v1.api_keys import router as api_keys_router  # noqa: E402

app.include_router(issuers_router, prefix="/api/v1")
app.include_router(securities_router, prefix="/api/v1")
app.include_router(listings_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
