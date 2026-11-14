"""Shared fixtures for the cloud API tests."""

from __future__ import annotations

import os

import pytest

from cloud_api.db import SCHEMA_PATH, open_connection


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
