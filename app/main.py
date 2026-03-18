from fastapi import FastAPI

app = FastAPI(
    title="Secmaster API",
    description="OTC/Microcap Security Master Data",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


from app.api.v1.issuers import router as issuers_router  # noqa: E402
from app.api.v1.securities import router as securities_router  # noqa: E402
from app.api.v1.listings import router as listings_router  # noqa: E402

app.include_router(issuers_router, prefix="/api/v1")
app.include_router(securities_router, prefix="/api/v1")
app.include_router(listings_router, prefix="/api/v1")
