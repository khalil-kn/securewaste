"""Shared fixtures for the cloud API tests."""

from __future__ import annotations

import os
import uuid

import pytest

from cloud_api.app import create_app
from cloud_api.config import Settings
from cloud_api.db import SCHEMA_PATH, open_connection

# Fake bearer tokens of the test suite. They are not credentials of any real service.
TEST_USERS = {
    "employee-token": "employee",
    "admin-token": "admin",
    "security-token": "security_officer",
    "auditor-token": "auditor",
}


@pytest.fixture(scope="session")
def database_url() -> str:
    """The PostgreSQL URL of the test database. The tests are skipped without it."""
    url = os.environ.get("CLOUD_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("CLOUD_DATABASE_URL is not set")
    return url


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    """Fail with an instruction when the migration has not been applied yet."""
    with open_connection(database_url) as connection:
        row = connection.execute("SELECT to_regclass('scan_events') AS table_name").fetchone()
    if row is None or row["table_name"] is None:
        pytest.fail(f"scan_events is missing: apply {SCHEMA_PATH} before running these tests")
    return database_url


@pytest.fixture
def db_connection(migrated_database: str):
    """A connection to the migrated test database."""
    with open_connection(migrated_database) as connection:
        yield connection


@pytest.fixture
def app(migrated_database: str):
    """The cloud API, wired to the test database and to the test tokens."""
    return create_app(Settings(database_url=migrated_database), tokens=TEST_USERS)


@pytest.fixture
def client(app):
    """A test client of the cloud API."""
    return app.test_client()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """The authorization header of a token that may store scan events."""
    return {"Authorization": "Bearer employee-token"}


@pytest.fixture
def valid_payload() -> dict:
    """A request body that matches the metadata contract."""
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": "2026-11-20T10:30:00Z",
        "classification": "Confidential",
        "risk": "High",
        "counts": {"email": 2, "phone": 1, "keyword": 3},
    }
