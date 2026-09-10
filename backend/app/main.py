"""
CloudPulse API — backend de demostración de arquitectura cloud.
FastAPI + PostgreSQL. Endpoints de salud, estado y pings.

Arquitectura (para portafolio):
  Android (HTTPS) -> Caddy (TLS/443) -> API (FastAPI :8000) -> PostgreSQL :5432
"""
import os
import platform
import time
import uuid
from datetime import datetime, timezone

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
REGION = os.getenv("REGION", "us-east-1")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cloudpulse:cloudpulse@db:5432/cloudpulse")

STARTED_AT = datetime.now(timezone.utc)

app = FastAPI(
    title="CloudPulse API",
    description="API pública de CloudPulse (app de portafolio). Expone estado del sistema y un endpoint de ping persistente.",
    version=APP_VERSION,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # API pública de demostración
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _db_connect():
    return psycopg.connect(DATABASE_URL, connect_timeout=3)


def _init_db():
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS pings (
                    id         BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    source     TEXT NOT NULL DEFAULT 'unknown'
                );
                CREATE INDEX IF NOT EXISTS idx_pings_created_at ON pings (created_at DESC);
                """
            )
        conn.commit()


def _db_latency_ms():
    t0 = time.perf_counter()
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    return round((time.perf_counter() - t0) * 1000, 1)


def _uptime_seconds():
    return int(time.time() - STARTED_AT.timestamp())


@app.on_event("startup")
def on_startup():
    _init_db()


@app.get("/")
def root():
    return {
        "app": "CloudPulse API",
        "version": APP_VERSION,
        "docs": "/docs",
        "endpoints": ["/healthz", "/api/v1/status", "/api/v1/ping", "/api/v1/pings"],
    }


@app.get("/healthz")
def healthz():
    """Health check plano para balanceadores/monitores (sin dependencias de lógica)."""
    try:
        with _db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        db = "up"
    except Exception:
        db = "down"
    status = "ok" if db == "up" else "degraded"
    return {"status": status, "db": db, "version": APP_VERSION, "uptime_s": _uptime_seconds()}


@app.get("/api/v1/status")
def status():
    """Estado completo que consume la app Android."""
    try:
        latency = _db_latency_ms()
        db_status = "up"
        with _db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM pings")
                total_pings = cur.fetchone()[0]
                cur.execute("SELECT MAX(created_at) FROM pings")
                last_ping = cur.fetchone()[0]
    except Exception as exc:  # noqa: BLE001
        db_status = "down"
        latency = None
        total_pings = None
        last_ping = None
        print("db error:", exc)
    return {
        "app": "CloudPulse",
        "version": APP_VERSION,
        "status": "ok" if db_status == "up" else "degraded",
        "server": {
            "hostname": platform.node(),
            "region": REGION,
            "platform": platform.system() + " " + platform.release(),
            "python": platform.python_version(),
            "started_at": STARTED_AT.isoformat(),
            "uptime_s": _uptime_seconds(),
        },
        "database": {
            "status": db_status,
            "latency_ms": latency,
            "total_pings": total_pings,
            "last_ping_at": last_ping.isoformat() if last_ping else None,
        },
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/ping", status_code=201)
def create_ping(request: Request):
    """Escribe un registro (prueba de la ruta de escritura App -> API -> DB)."""
    source = request.headers.get("User-Agent", "unknown")[:120] or "unknown"
    ping_id = str(uuid.uuid4())[:8]
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO pings (source) VALUES (%s) RETURNING id, created_at", (source,))
            row = cur.fetchone()
        conn.commit()
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pings")
            total = cur.fetchone()[0]
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
def list_pings(limit: int = 10):
    """Historial reciente de pings (prueba de la ruta de lectura)."""
    limit = max(1, min(limit, 50))
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, source, created_at FROM pings ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
    return {"pings": [{"id": r[0], "source": r[1], "created_at": r[2].isoformat()} for r in rows]}


@app.exception_handler(Exception)
async def unhandled(_request: Request, _exc: Exception):
    return JSONResponse(status_code=500, content={"status": "error", "detail": "internal_error"})
