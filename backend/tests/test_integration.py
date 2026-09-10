"""Integration test: the real API against a real PostgreSQL.

Run in CI with a PostgreSQL service container (see ``.github/workflows/ci.yml``) or locally with::

    make up
    cd backend && DATABASE_URL=postgresql://cloudpulse:...@127.0.0.1:5432/cloudpulse pytest tests/test_integration.py

This is the test that would fail if the SQL, the schema bootstrap or the aggregate query broke — the unit
tests use a fake connection and cannot catch that.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="set DATABASE_URL to run the integration test",
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from app import main  # imported here so the skip check runs first

    with TestClient(main.app) as test_client:
        yield test_client


def test_health_ok(client: TestClient) -> None:
    assert client.get("/healthz").json()["db"] == "up"


def test_ping_is_persisted_and_counted(client: TestClient) -> None:
    before = client.get("/api/v1/status").json()["database"]["total_pings"]
    created = client.post("/api/v1/ping", headers={"User-Agent": "integration-test"}).json()
    after = client.get("/api/v1/status").json()["database"]["total_pings"]

    assert created["db_row_id"] > 0
    assert after == before + 1


def test_history_returns_the_row_we_just_wrote(client: TestClient) -> None:
    client.post("/api/v1/ping", headers={"User-Agent": "integration-test"})
    latest = client.get("/api/v1/pings?limit=1").json()["pings"][0]
    assert latest["source"] == "integration-test"


def test_schema_is_bootstrapped_idempotently(client: TestClient) -> None:
    """Hitting the API twice must not fail on an existing table or index."""
    assert client.get("/healthz").status_code == 200
    assert client.get("/healthz").status_code == 200
