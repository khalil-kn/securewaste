"""PostgreSQL access for the cloud metadata API.

Only metadata is stored here: counts, classification and risk. Document text, filenames, paths
and matched values never reach this module (ADR-0006: a raw value never leaves detection).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

# The migration script of this service. It is applied by the operator (CI and the local setup in
# cloud_api/README.md), so the DDL lives in exactly one place.
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class DuplicateEventError(Exception):
    """Raised when an event_id has already been stored."""


def connect(database_url: str) -> psycopg.Connection[dict[str, Any]]:
    """Open a connection that returns rows as dicts."""
    return psycopg.Connection[dict[str, Any]].connect(database_url, row_factory=dict_row)


@contextmanager
def open_connection(database_url: str) -> Iterator[psycopg.Connection[dict[str, Any]]]:
    """Open a connection and close it when the block ends."""
    connection = connect(database_url)
    try:
        yield connection
    finally:
        connection.close()


def insert_scan_event(
    connection: psycopg.Connection[dict[str, Any]],
    *,
    event_id: str,
    event_timestamp: datetime,
    classification: str,
    risk: str,
    email_count: int,
    phone_count: int,
    keyword_count: int,
) -> dict[str, Any]:
    """Store one scan event and return the stored row."""
    try:
        row = connection.execute(
            """
            INSERT INTO scan_events (
                event_id, event_timestamp, classification, risk,
                email_count, phone_count, keyword_count
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING event_id, event_timestamp, classification, risk,
                      email_count, phone_count, keyword_count, received_at
            """,
            (
                event_id,
                event_timestamp,
                classification,
                risk,
                email_count,
                phone_count,
                keyword_count,
            ),
        ).fetchone()
    except psycopg.errors.UniqueViolation as exc:
        connection.rollback()
        raise DuplicateEventError(f"event_id already stored: {event_id}") from exc
    if row is None:
        raise RuntimeError("the database returned no row for the inserted event")
    connection.commit()
    return row


def get_scan_event(connection: psycopg.Connection[dict[str, Any]], event_id: str) -> dict[str, Any] | None:
    """Return one stored event, or None when the event_id is unknown."""
    row = connection.execute(
        """
        SELECT event_id, event_timestamp, classification, risk,
               email_count, phone_count, keyword_count, received_at
        FROM scan_events
        WHERE event_id = %s
        """,
        (event_id,),
    ).fetchone()
    return row
