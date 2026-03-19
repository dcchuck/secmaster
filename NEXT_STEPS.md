# Next Steps

## What's Done

The backend implementation plan (Tasks 1–20) is complete:

- **Data layer:** 12 SQLModel tables with Alembic migrations, point-in-time effective dating
- **API:** REST endpoints for issuers, securities, listings with `as_of` filtering, cursor pagination
- **Auth:** Clerk JWT verification + API key resolution with user auto-sync
- **API keys:** Create/list/delete endpoints, paid tier enforcement
- **Rate limiting:** slowapi, 60 req/min default
- **Ingestion:** BaseIngestor abstract class, Fidelity stub, CLI entrypoint
- **Infrastructure:** Dockerfile, docker-compose (app + dev/test Postgres), mise-en-place tooling
- **Tests:** 41 passing tests covering models, services, API endpoints, auth, and ingestion

## Manual Testing

```bash
mise run db:up       # start Postgres containers
mise run migrate     # apply migrations to dev DB
mise run dev         # start FastAPI on localhost:8000
```

- `GET localhost:8000/health` — health check
- `GET localhost:8000/docs` — Swagger UI (all endpoints documented)
- Data endpoints require auth (401 without token/key)

## Remaining Work

### Clerk Setup

Auth endpoints are wired but need a real Clerk project:

1. Create a Clerk application at https://clerk.com
2. Set `CLERK_SECRET_KEY` and `CLERK_JWKS_URL` in `.env`
3. Test JWT flow end-to-end via Swagger UI or curl with a Bearer token

### Fidelity Ingestor

The stub exists at `app/ingestion/fidelity.py`. Port the existing Fidelity ingestion work into the `BaseIngestor` interface:

- Implement `fetch()` — pull raw data from Fidelity source
- Implement `transform()` — normalize into canonical SQLModel instances
- Run via `python -m app.ingestion.cli fidelity`

### Frontend (React + TypeScript)

The spec calls for a separate implementation plan covering:

- React + TypeScript + Vite setup
- Pages: login, issuer list, issuer profile, security profile, listing profile, API key management
- TanStack Query for server state
- Auto-generated API client from OpenAPI spec
- Clerk React SDK for auth

### Additional Vendor Ingestors

Subclass `BaseIngestor` for each new vendor. The interface is:

```python
class MyVendorIngestor(BaseIngestor):
    vendor_name = "my_vendor"
    def fetch(self) -> list[RawRecord]: ...
    def transform(self, raw) -> list[SQLModel]: ...
```

Register in `app/ingestion/cli.py` INGESTORS dict.

### Production Deployment

- Configure production database (managed Postgres)
- Set environment variables for Clerk, database URL
- Deploy via Fly.io, Railway, or AWS (Dockerfile is ready)
- Consider adding health check to deployment config
- Set up CI/CD (run `mise run test` in pipeline)
