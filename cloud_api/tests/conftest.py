"""Shared fixtures for the cloud API tests."""

from __future__ import annotations

import os
import uuid

import pytest  # pyright: ignore[reportMissingImports]

from cloud_api.app import create_app
from cloud_api.auth import Role, new_credential, parse_credentials
from cloud_api.config import Settings
from cloud_api.db import SCHEMA_PATH, open_connection

# Test identities. None of these is a real person or service.
EMPLOYEE_ID = "11111111-2222-3333-4444-555555555555"
OTHER_EMPLOYEE_ID = "66666666-7777-8888-9999-000000000000"
ADMIN_EMPLOYEE_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
SECURITY_OFFICER_ID = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"

# Aliases used by test_auth.py
EMPLOYEE_A = EMPLOYEE_ID
EMPLOYEE_B = OTHER_EMPLOYEE_ID

TEST_USERS = {
    "employee_a": (Role.EMPLOYEE, EMPLOYEE_ID),
    "employee_b": (Role.EMPLOYEE, OTHER_EMPLOYEE_ID),
    "admin": (Role.ADMIN, ADMIN_EMPLOYEE_ID),
    "security_officer": (Role.SECURITY_OFFICER, SECURITY_OFFICER_ID),
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
def auth_tokens() -> dict[str, tuple[str, str]]:
    """name -> (plaintext token, config entry). Fresh random tokens for every test."""
    return {name: new_credential(role, employee_id, 3600) for name, (role, employee_id) in TEST_USERS.items()}


@pytest.fixture
def credentials(auth_tokens):
    """The parsed credential mapping the app validates against (hashes only)."""
    return parse_credentials(",".join(entry for _token, entry in auth_tokens.values()))


@pytest.fixture
def app(migrated_database: str, credentials):
    """The cloud API, wired to the test database and to the test credentials."""
    return create_app(Settings(database_url=migrated_database), credentials=credentials)


@pytest.fixture
def client(app):
    """A test client of the cloud API."""
    return app.test_client()


@pytest.fixture
def bearer(auth_tokens):
    """bearer("admin") -> {"Authorization": "Bearer <token>"} for a named test user."""

    def _bearer(name: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {auth_tokens[name][0]}"}

    return _bearer


@pytest.fixture
def auth_headers(bearer) -> dict[str, str]:
    """The authorization header of an employee token (may store scan events)."""
    return bearer("employee_a")


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


@pytest.fixture
def new_event(valid_payload):
    """Factory for a valid payload with a fresh event_id, for tests storing several events."""

    def _new_event(**overrides) -> dict:
        return {**valid_payload, "event_id": str(uuid.uuid4()), **overrides}

    return _new_event
