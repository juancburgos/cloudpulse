"""CloudPulse API — a small but production-shaped service.

Exposes the health of its own stack (API + PostgreSQL) so the Android client, a browser or a
monitoring probe can render live status. Three endpoints and one table, deliberately.

Request path in production:

    Android (HTTPS) -> Caddy (TLS termination) -> this API (localhost) -> PostgreSQL

See ``docs/ARCHITECTURE.md`` for the full picture and ``docs/ADR/`` for the decisions behind it.
"""

import os
import platform
import threading
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
REGION = os.getenv("REGION", "us-east-1")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cloudpulse:cloudpulse@db:5432/cloudpulse")

# The only write endpoint is public and unauthenticated, so it is metered per client address.
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "20"))
RATE_LIMIT_WINDOW_S = float(os.getenv("RATE_LIMIT_WINDOW_S", "60"))

STARTED_AT = datetime.now(UTC)


class _BootState:
    """Process state that outlives a request: whether the schema has been created yet.

    Held in an object rather than a module-level boolean so the health probe can update it
    without a ``global`` statement.
    """

    schema_ready = False


_BOOT = _BootState()


class RateLimiter:
    """Fixed-window request counter, per client, held in process memory (ADR-0005).

    Deliberately not Redis: the API runs as one container on one host, and the goal is to keep a
    public write endpoint from being used as a free database filler, not to bill traffic per user.
    Becoming multi-instance is the point at which this decision has to be revisited, and ADR-0005
    says so explicitly.
    """

    def __init__(self, limit: int, window_s: float, max_keys: int = 10_000) -> None:
        self._limit = limit
        self._window_s = window_s
        self._max_keys = max_keys
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> tuple[bool, int]:
        """Register one hit for ``key``. Returns ``(allowed, retry_after_seconds)``."""
        current = time.monotonic() if now is None else now
        with self._lock:
            window_start, count = self._hits.get(key, (current, 0))
            if current - window_start >= self._window_s:
                window_start, count = current, 0
            count += 1
            self._hits[key] = (window_start, count)

            if len(self._hits) > self._max_keys:
                self._prune(current)

            if count > self._limit:
                return False, max(1, int(window_start + self._window_s - current) + 1)
        return True, 0

    def _prune(self, now: float) -> None:
        """Drop expired windows: bounds memory when many distinct addresses call in."""
        stale = [k for k, (start, _) in self._hits.items() if now - start >= self._window_s]
        for key in stale:
            del self._hits[key]
        if not stale:  # every window is live: a burst from many distinct addresses, so reset
            self._hits.clear()

    @property
    def tracked_clients(self) -> int:
        """How many client windows are currently held, so the bound is observable and testable."""
        return len(self._hits)


_limiter = RateLimiter(RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_S)


def _client_ip(request: Request) -> str:
    """Client address, honouring the proxy header.

    Caddy either appends the peer it saw to a caller-supplied ``X-Forwarded-For`` or overwrites it
    with that peer; in both cases the **right-most** entry is the address the proxy vouched for,
    while the left-most is whatever the caller typed. Reading the first entry would let any client
    choose its own bucket — and therefore never be throttled.

    Direct calls that bypass the proxy (tests, local curl) have no header and fall back to the
    socket peer; in production that path does not exist, because the API is bound to loopback.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


SCHEMA = """
CREATE TABLE IF NOT EXISTS pings (
    id         BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source     TEXT NOT NULL DEFAULT 'unknown'
);
CREATE INDEX IF NOT EXISTS idx_pings_created_at ON pings (created_at DESC);
"""


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap the schema once per process, before serving traffic."""
    _init_db()
    yield


app = FastAPI(
    title="CloudPulse API",
    description=(
        "Public API of CloudPulse, a portfolio app that shows the live status of this backend. "
        "Exposes system health and a persistent ping endpoint."
    ),
    version=APP_VERSION,
    docs_url="/docs",
    lifespan=lifespan,
)

# The API is public and carries no credentials, cookies or personal data, so the demo landing
# page is allowed to call it straight from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _db_connect() -> psycopg.Connection:
    """Open a short-lived connection. A 3 s timeout keeps the health probe honest."""
    return psycopg.connect(DATABASE_URL, connect_timeout=3)


def _init_db() -> None:
    """Create the schema if it is missing.

    Deliberately non-fatal: if PostgreSQL is not ready yet, the process must still start and
    answer ``/healthz`` with ``db: down`` instead of crash-looping. The next health probe that
    reaches the database retries the bootstrap (ADR-0004).
    """
    try:
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute(SCHEMA)
            conn.commit()
    except Exception as exc:  # noqa: BLE001 - a slow database must not block startup
        print("schema bootstrap deferred, database not ready:", exc)
        return
    _BOOT.schema_ready = True


def _db_latency_ms() -> float:
    """Round-trip time of a trivial query, used as a cheap dependency signal."""
    started = time.perf_counter()
    with _db_connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
    return round((time.perf_counter() - started) * 1000, 1)


def _uptime_seconds() -> int:
    return int(time.time() - STARTED_AT.timestamp())


@app.get("/")
def root() -> dict:
    return {
        "app": "CloudPulse API",
        "version": APP_VERSION,
        "docs": "/docs",
        "endpoints": ["/healthz", "/api/v1/status", "/api/v1/ping", "/api/v1/pings"],
    }


@app.get("/healthz")
def healthz() -> dict:
    """Cheap dependency probe for containers, load balancers and uptime monitors.

    Returns 200 even when the database is down; the degradation travels in the body so a
    reachable-but-partially-broken instance is distinguishable from a dead one (ADR-0004).
    """
    try:
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        db_state = "up"
    except Exception:  # noqa: BLE001 - any failure means "dependency down"
        db_state = "down"
    else:
        if not _BOOT.schema_ready:  # the database just became reachable: finish the boot
            _init_db()
    return {
        "status": "ok" if db_state == "up" else "degraded",
        "db": db_state,
        "version": APP_VERSION,
        "uptime_s": _uptime_seconds(),
    }


@app.get("/api/v1/status")
def status() -> dict:
    """Composite payload rendered by the Android client in a single round trip."""
    try:
        latency = _db_latency_ms()
        db_state = "up"
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pings")
            total_pings = cur.fetchone()[0]
            cur.execute("SELECT MAX(created_at) FROM pings")
            last_ping = cur.fetchone()[0]
    except Exception as exc:  # noqa: BLE001 - report degradation instead of failing
        db_state = "down"
        latency = None
        total_pings = None
        last_ping = None
        print("database error while building status:", exc)

    return {
        "app": "CloudPulse",
        "version": APP_VERSION,
        "status": "ok" if db_state == "up" else "degraded",
        "server": {
            "hostname": platform.node(),
            "region": REGION,
            "platform": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "started_at": STARTED_AT.isoformat(),
            "uptime_s": _uptime_seconds(),
        },
        "database": {
            "status": db_state,
            "latency_ms": latency,
            "total_pings": total_pings,
            "last_ping_at": last_ping.isoformat() if last_ping else None,
        },
        "time": datetime.now(UTC).isoformat(),
    }


@app.post(
    "/api/v1/ping",
    status_code=201,
    # The handler returns either the created payload or a 429 envelope, so there is no single
    # response model for FastAPI to infer from the annotation.
    response_model=None,
    responses={429: {"description": "Rate limit exceeded"}},
)
def create_ping(request: Request) -> dict | JSONResponse:
    """Write one row and report the resulting total: the write *and* read paths in one call.

    Metered per client address (ADR-0005): this endpoint is public and every call costs a row.
    """
    allowed, retry_after = _limiter.check(_client_ip(request))
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "status": "throttled",
                "detail": "rate_limit_exceeded",
                "limit": RATE_LIMIT_MAX,
                "window_s": int(RATE_LIMIT_WINDOW_S),
            },
            headers={"Retry-After": str(retry_after)},
        )

    source = request.headers.get("User-Agent", "unknown")[:120] or "unknown"
    ping_id = str(uuid.uuid4())[:8]

    with _db_connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pings (source) VALUES (%s) RETURNING id, created_at",
            (source,),
        )
        row = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM pings")
        total = cur.fetchone()[0]
        conn.commit()

    return {
        "ok": True,
        "ping_id": ping_id,
        "db_row_id": row[0],
        "created_at": row[1].isoformat(),
        "total_pings": total,
        "server_version": APP_VERSION,
        "region": REGION,
    }


@app.get("/api/v1/pings")
def list_pings(limit: int = 10) -> dict:
    """Most recent pings, newest first. ``limit`` is clamped instead of rejected."""
    limit = max(1, min(limit, 50))
    with _db_connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, source, created_at FROM pings ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
    return {
        "pings": [
            {"id": row[0], "source": row[1], "created_at": row[2].isoformat()} for row in rows
        ]
    }


@app.exception_handler(Exception)
async def unhandled(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"status": "error", "detail": "internal_error"})
