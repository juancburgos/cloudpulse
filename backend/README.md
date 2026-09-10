# CloudPulse — FastAPI service

Three endpoints, one table, explicit failure semantics. Roughly 150 lines of Python; read
`app/main.py` top to bottom and you have seen the whole service.

```
backend/
├── app/main.py             # the service (routes, SQL, degradation logic)
├── tests/test_api.py       # unit tests with a fake database connection (no infrastructure)
├── tests/test_integration.py  # contract tests against a real PostgreSQL (run in CI)
├── requirements.txt        # runtime dependencies (pinned)
├── requirements-dev.txt    # pytest, httpx, ruff
├── pyproject.toml          # pytest + ruff configuration
└── Dockerfile              # python:3.12-slim, uvicorn with 2 workers
```

## Endpoints

| Method | Path | Purpose | Touches the database |
|---|---|---|---|
| GET | `/healthz` | Cheap probe for containers and monitors | `SELECT 1` only |
| GET | `/api/v1/status` | Everything the app renders | latency probe + aggregates |
| POST | `/api/v1/ping` | Records a ping (the write path) | `INSERT` + `COUNT` |
| GET | `/api/v1/pings?limit=N` | Recent history, `limit` clamped to 1..50 | one indexed read |
| GET | `/docs` | OpenAPI/Swagger UI | no |

Contract details, example payloads and error semantics: [`../docs/API.md`](../docs/API.md).

## Running locally

```bash
# from the repository root
cp .env.example .env
make up          # docker compose: api + db
make smoke       # end-to-end verification
make test        # unit tests (fast, no infrastructure)
make lint        # ruff check + format check
```

Or without Docker, pointing at any PostgreSQL:

```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/cloudpulse \
  uvicorn app.main:app --reload --port 8001
```

## Notes on the implementation

- **Schema bootstrap is idempotent** (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) so a fresh
  volume and an existing one behave identically on start.
- **No connection pool on purpose.** With two workers and a handful of requests per minute, a pool adds
  lifecycle to reason about and saves nothing measurable. It becomes the right call at higher request rates —
  and it is documented as such rather than pretended away.
- **`connect_timeout=3`** bounds the health probe: a slow database must fail fast, not occupy a worker.
- **Degradation travels in the body**, not in the HTTP status code — see ADR-0004 for the trade-off.
- **CORS is open** because the API serves no credentials and no personal data; the demo landing page fetches it
  directly from the browser.
