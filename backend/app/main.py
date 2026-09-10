"""CloudPulse API — a small but production-shaped service.

Exposes the health of its own stack (API + PostgreSQL) so the Android client, a browser or a
monitoring probe can render live status. Three endpoints and one table, deliberately.

Request path in production:

    Android (HTTPS) -> Caddy (TLS termination) -> this API (localhost) -> PostgreSQL

See ``docs/ARCHITECTURE.md`` for the full picture and ``docs/ADR/`` for the decisions behind it.
"""

import os
import platform
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

STARTED_AT = datetime.now(UTC)

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
    with _db_connect() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA)
        conn.commit()


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


@app.post("/api/v1/ping", status_code=201)
def create_ping(request: Request) -> dict:
    """Write one row and report the resulting total: the write *and* read paths in one call."""
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
