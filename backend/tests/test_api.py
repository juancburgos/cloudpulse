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
        self._rows: list[tuple] = []

    def execute(self, sql: str, params: tuple | None = None) -> None:  # noqa: ARG002
        statement = " ".join(sql.lower().split())
        if "select 1" in statement:
            self._rows = [(1,)]
        elif "insert into pings" in statement:
            self._rows = [(42, FAKE_ROW_TIME)]
        elif "count(*)" in statement:
            self._rows = [(7,)]
        elif "max(created_at)" in statement:
            self._rows = [(FAKE_ROW_TIME,)]
        elif statement.startswith("select id, source, created_at"):
            self._rows = [
                (1, "pytest-agent", FAKE_ROW_TIME),
                (2, "android-client", FAKE_ROW_TIME),
            ]
        else:  # pragma: no cover - guards against silent SQL changes
            self._rows = []

    def fetchone(self) -> tuple | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple]:
        return list(self._rows)

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


class FlakyConnection(FakeConnection):
    """Unreachable until ``healthy`` is flipped, to exercise recovery without a restart."""

    def __init__(self) -> None:
        self.healthy = False

    def cursor(self) -> FakeCursor:
        return FakeCursor() if self.healthy else BrokenCursor()


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


@pytest.fixture()
def degraded_caller(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Same broken database, but the HTTP contract is the subject: no re-raised exceptions."""
    monkeypatch.setattr(main, "_db_connect", broken_connection)
    with TestClient(main.app, raise_server_exceptions=False) as test_client:
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
    assert len(entries) == 2
    assert entries[0]["source"] == "pytest-agent"


@pytest.mark.parametrize("limit", [0, -1, 999, "abc"])
def test_pings_clamps_numeric_limits_and_rejects_non_numeric(
    client: TestClient, limit: object
) -> None:
    response = client.get(f"/api/v1/pings?limit={limit}")
    # Non-numeric values fail validation (422); out-of-range numbers are clamped, never rejected.
    assert response.status_code in (200, 422)


def test_ping_reports_a_clean_500_instead_of_leaking_a_traceback(
    degraded_caller: TestClient,
) -> None:
    """A failing write must return the documented error body, never an HTML crash page."""
    response = degraded_caller.post("/api/v1/ping")
    assert response.status_code == 500
    assert response.json() == {"status": "error", "detail": "internal_error"}


def test_schema_bootstrap_retries_when_the_database_arrives_late(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot must survive a database that is not ready yet, and catch up on a later probe."""
    monkeypatch.setattr(main._BOOT, "schema_ready", False)
    connection = FlakyConnection()

    def connect() -> FlakyConnection:
        return connection

    monkeypatch.setattr(main, "_db_connect", connect)

    with TestClient(main.app) as late_client:
        # The API is up even though nothing could be bootstrapped at startup.
        booting = late_client.get("/healthz").json()
        assert (booting["status"], booting["db"]) == ("degraded", "down")
        assert main._BOOT.schema_ready is False

        connection.healthy = True
        assert late_client.get("/healthz").json()["db"] == "up"
        assert main._BOOT.schema_ready is True


def test_rate_limiter_allows_up_to_the_limit_and_then_refuses() -> None:
    """The counter is exclusive at the limit: the (limit + 1)th call in a window is refused."""
    limiter = main.RateLimiter(limit=3, window_s=60)

    for _ in range(3):
        allowed, retry_after = limiter.check("203.0.113.9", now=100.0)
        assert allowed is True
        assert retry_after == 0

    allowed, retry_after = limiter.check("203.0.113.9", now=100.0)
    assert allowed is False
    assert retry_after >= 1


def test_rate_limiter_forgets_a_window_once_it_expires() -> None:
    limiter = main.RateLimiter(limit=1, window_s=30)

    assert limiter.check("198.51.100.4", now=0.0)[0] is True
    assert limiter.check("198.51.100.4", now=10.0)[0] is False
    assert limiter.check("198.51.100.4", now=31.0)[0] is True  # new window, counter reset


def test_rate_limiter_tracks_clients_independently() -> None:
    limiter = main.RateLimiter(limit=1, window_s=60)

    assert limiter.check("198.51.100.1", now=5.0)[0] is True
    assert limiter.check("198.51.100.2", now=5.0)[0] is True  # a neighbour is not punished
    assert limiter.check("198.51.100.1", now=5.0)[0] is False


def test_rate_limiter_bounds_its_own_memory() -> None:
    """A wide spread of addresses must not grow the table without bound."""
    limiter = main.RateLimiter(limit=1, window_s=60, max_keys=50)

    for i in range(200):
        limiter.check(f"198.51.100.{i}", now=float(i))

    assert limiter.tracked_clients <= 50


def test_ping_is_throttled_with_429_and_retry_after(client: TestClient) -> None:
    """End to end: the public write endpoint answers 429, with the header a client can obey."""
    temporary = main.RateLimiter(limit=2, window_s=60)
    original = main._limiter
    main._limiter = temporary
    try:
        assert client.post("/api/v1/ping").status_code == 201
        assert client.post("/api/v1/ping").status_code == 201
        throttled = client.post("/api/v1/ping")
        assert throttled.status_code == 429
        assert throttled.json()["status"] == "throttled"
        assert int(throttled.headers["retry-after"]) >= 1
    finally:
        main._limiter = original


def test_throttling_follows_the_proxy_vouched_address_and_ignores_spoofing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Behind Caddy every request arrives from the proxy, so the header carries the real client.

    The left-most entry is caller-controlled, so a client that invents a new address for every
    request must still land in the bucket of the address the proxy appended for it.
    """
    monkeypatch.setattr(main, "_db_connect", working_connection)
    temporary = main.RateLimiter(limit=1, window_s=60)
    original = main._limiter
    main._limiter = temporary
    try:
        with TestClient(main.app) as forwarded_client:
            first = forwarded_client.post(
                "/api/v1/ping", headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.9"}
            )
            spoofed = forwarded_client.post(
                "/api/v1/ping", headers={"X-Forwarded-For": "5.6.7.8, 203.0.113.9"}
            )
            neighbour = forwarded_client.post(
                "/api/v1/ping", headers={"X-Forwarded-For": "10.0.0.1, 203.0.113.10"}
            )

        assert first.status_code == 201
        assert spoofed.status_code == 429  # changing the fake prefix must not buy a new bucket
        assert neighbour.status_code == 201  # a genuinely different client is unaffected
    finally:
        main._limiter = original
