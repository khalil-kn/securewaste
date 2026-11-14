"""PostgreSQL access for the cloud metadata API.

Only metadata is stored here: counts, classification and risk. Document text, filenames, paths
and matched values never reach this module (ADR-0006: a raw value never leaves detection).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, LiteralString, cast

import psycopg
from psycopg.rows import dict_row

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class DuplicateEventError(Exception):
    """Raised when an event_id has already been stored."""


def connect(database_url: str) -> psycopg.Connection[dict[str, Any]]:
    """Open a connection that returns rows as dicts."""
    return psycopg.Connection[dict[str, Any]].connect(database_url, row_factory=dict_row)


def apply_schema(connection: psycopg.Connection[dict[str, Any]], schema_path: Path = SCHEMA_PATH) -> None:
    """Create the tables if they do not exist yet. Safe to run on every start.

    The script is a file of this repository, not user input. psycopg only accepts literal
    queries, so the cast states that this query is trusted.
    """
    connection.execute(cast("LiteralString", schema_path.read_text(encoding="utf-8")))
    connection.commit()


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
