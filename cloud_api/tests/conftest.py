"""Shared fixtures for the cloud API tests."""

from __future__ import annotations

import os

import pytest

from cloud_api.db import apply_schema, connect


@pytest.fixture(scope="session")
def database_url() -> str:
    """The PostgreSQL URL of the test run, or skip when no database is configured."""
    url = os.environ.get("CLOUD_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("CLOUD_DATABASE_URL is not set: there is no PostgreSQL to test against")
    return url


@pytest.fixture()
def db_connection(database_url: str):
    """A connection to a database that already carries the schema."""
    with connect(database_url) as connection:
        apply_schema(connection)
        yield connection
