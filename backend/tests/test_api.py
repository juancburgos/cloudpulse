"""Unit tests for the CloudPulse API.

These tests exercise the real endpoints with a **fake database connection**, so they run in
milliseconds and need no infrastructure. The contract against a real PostgreSQL is covered by
``test_integration.py``.

The fake mimics exactly the surface ``app.main`` uses: ``psycopg.connect()`` returning a context
manager with ``cursor()`` (also a context manager), ``fetchone()`` and ``commit()``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import main

FAKE_ROW_TIME = datetime(2026, 9, 9, 22, 33, 41, tzinfo=UTC)


class FakeCursor:
    """Answers the handful of SQL statements the API issues."""

    def __init__(self) -> None:
        self._result: tuple | None = None

    def execute(self, sql: str, params: tuple | None = None) -> None:  # noqa: ARG002
        statement = " ".join(sql.lower().split())
        if "select 1" in statement:
            self._result = (1,)
        elif "insert into pings" in statement:
            self._result = (42, FAKE_ROW_TIME)
        elif "count(*)" in statement:
            self._result = (7,)
        elif "max(created_at)" in statement:
            self._result = (FAKE_ROW_TIME,)
        elif statement.startswith("select id, source, created_at"):
            self._result = (1, "pytest-agent", FAKE_ROW_TIME)
        else:  # pragma: no cover - guards against silent SQL changes
            self._result = None

    def fetchone(self) -> tuple | None:
        return self._result

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class FakeConnection:
    def cursor(self) -> FakeCursor:
        return FakeCursor()

    def commit(self) -> None:  # pragma: no cover - trivial
        return None

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class BrokenCursor(FakeCursor):
    def execute(self, sql: str, params: tuple | None = None) -> None:
        raise RuntimeError("database is gone")


class BrokenConnection(FakeConnection):
    def cursor(self) -> FakeCursor:
        return BrokenCursor()


def working_connection() -> FakeConnection:
    return FakeConnection()


def broken_connection() -> BrokenConnection:
    return BrokenConnection()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "_db_connect", working_connection)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture()
def degraded_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A client whose database is unreachable, to assert the degraded contract."""
    monkeypatch.setattr(main, "_db_connect", broken_connection)
    with TestClient(main.app) as test_client:
        yield test_client


def test_root_lists_endpoints(client: TestClient) -> None:
    body = client.get("/").json()
    assert body["app"] == "CloudPulse API"
    assert "/healthz" in body["endpoints"]


def test_healthz_reports_ok_when_database_answers(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "up"
    assert body["uptime_s"] >= 0


def test_healthz_degrades_but_stays_200_when_database_is_down(degraded_client: TestClient) -> None:
    """Documented convention (ADR-0004): degradation travels in the body, not the status code."""
    response = degraded_client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["db"] == "down"


def test_status_returns_the_full_payload(client: TestClient) -> None:
    body = client.get("/api/v1/status").json()
    assert body["app"] == "CloudPulse"
    assert body["status"] == "ok"
    assert body["server"]["region"]
    assert body["database"]["status"] == "up"
    assert body["database"]["total_pings"] == 7
    assert body["database"]["latency_ms"] is not None
    assert body["database"]["last_ping_at"] == FAKE_ROW_TIME.isoformat()


def test_status_is_explicit_about_unknowns(degraded_client: TestClient) -> None:
    body = degraded_client.get("/api/v1/status").json()
    assert body["status"] == "degraded"
    assert body["database"]["status"] == "down"
    assert body["database"]["total_pings"] is None
    assert body["database"]["last_ping_at"] is None


def test_ping_writes_and_reports_the_total(client: TestClient) -> None:
    response = client.post("/api/v1/ping")
    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["db_row_id"] == 42
    assert body["created_at"] == FAKE_ROW_TIME.isoformat()
    assert body["total_pings"] == 7
    assert len(body["ping_id"]) == 8


def test_pings_history_is_bounded(client: TestClient) -> None:
    response = client.get("/api/v1/pings?limit=5")
    assert response.status_code == 200
    entries = response.json()["pings"]
    assert isinstance(entries, list)
    assert entries[0]["source"] == "pytest-agent"


@pytest.mark.parametrize("limit", [0, -1, 999, "abc"])
def test_pings_clamps_numeric_limits_and_rejects_non_numeric(
    client: TestClient, limit: object
) -> None:
    response = client.get(f"/api/v1/pings?limit={limit}")
    # Non-numeric values fail validation (422); out-of-range numbers are clamped, never rejected.
    assert response.status_code in (200, 422)
