"""SCRUM-27: the scan_events schema is minimal and survives an insert/read round trip."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import psycopg
import pytest

from cloud_api.db import DuplicateEventError, get_scan_event, insert_scan_event

# The only columns scan_events may ever have. A column that could hold document content
# (raw text, a filename, a path, a finding) would break the privacy contract of the API.
EXPECTED_COLUMNS = {
    "event_id",
    "event_timestamp",
    "classification",
    "risk",
    "email_count",
    "phone_count",
    "keyword_count",
    "received_at",
}


def _event(event_id: str | None = None) -> dict:
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "event_timestamp": datetime(2026, 11, 20, 10, 30, tzinfo=UTC),
        "classification": "Confidential",
        "risk": "High",
        "email_count": 2,
        "phone_count": 1,
        "keyword_count": 3,
    }


def test_insert_then_read_returns_the_stored_event(db_connection):
    event = _event()

    stored = insert_scan_event(db_connection, **event)

    assert str(stored["event_id"]) == event["event_id"]
    assert stored["event_timestamp"] == event["event_timestamp"]
    assert stored["classification"] == "Confidential"
    assert stored["risk"] == "High"
    assert stored["email_count"] == 2
    assert stored["phone_count"] == 1
    assert stored["keyword_count"] == 3
    assert stored["received_at"] is not None

    assert get_scan_event(db_connection, event["event_id"]) == stored


def test_reading_an_unknown_event_id_returns_nothing(db_connection):
    assert get_scan_event(db_connection, str(uuid.uuid4())) is None


def test_the_same_event_id_cannot_be_stored_twice(db_connection):
    event = _event()
    insert_scan_event(db_connection, **event)

    with pytest.raises(DuplicateEventError):
        insert_scan_event(db_connection, **event)


def test_scan_events_has_only_the_metadata_columns(db_connection):
    rows = db_connection.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'scan_events'
        """
    ).fetchall()

    assert {row["column_name"] for row in rows} == EXPECTED_COLUMNS


@pytest.mark.parametrize(
    ("field", "value_outside_the_contract"),
    [("classification", "Secret"), ("risk", "Critical")],
)
def test_the_database_rejects_values_outside_the_contract(db_connection, field, value_outside_the_contract):
    event = _event()
    event[field] = value_outside_the_contract

    with pytest.raises(psycopg.errors.CheckViolation):
        insert_scan_event(db_connection, **event)
    db_connection.rollback()
