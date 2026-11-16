"""Tests of the privacy invariant: only metadata may be stored or echoed."""

from __future__ import annotations

from cloud_api.db import get_scan_event

STORED_COLUMNS = {
    "event_id",
    "event_timestamp",
    "classification",
    "risk",
    "email_count",
    "phone_count",
    "keyword_count",
    "received_at",
}


def test_the_stored_row_holds_the_metadata_only(client, auth_headers, valid_payload, db_connection):
    response = client.post("/api/v1/scans", json=valid_payload, headers=auth_headers)
    assert response.status_code == 201

    stored = get_scan_event(db_connection, valid_payload["event_id"])
    assert stored is not None
    assert set(stored) == STORED_COLUMNS
    assert stored["classification"] == valid_payload["classification"]
    assert stored["risk"] == valid_payload["risk"]
    assert stored["email_count"] == valid_payload["counts"]["email"]
    assert stored["phone_count"] == valid_payload["counts"]["phone"]
    assert stored["keyword_count"] == valid_payload["counts"]["keyword"]


def test_content_that_is_refused_is_neither_stored_nor_echoed(client, auth_headers, valid_payload, db_connection):
    sentinel = "customer@example.com"
    response = client.post(
        "/api/v1/scans",
        json={**valid_payload, "raw_text": sentinel},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert sentinel not in response.get_data(as_text=True)

    rows = db_connection.execute("SELECT * FROM scan_events").fetchall()
    assert all(sentinel not in str(value) for row in rows for value in row.values())


def test_no_column_of_the_table_can_hold_a_document(client, auth_headers, valid_payload, db_connection):
    client.post("/api/v1/scans", json=valid_payload, headers=auth_headers)
    columns = db_connection.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'scan_events'"
    ).fetchall()
    names = {column["column_name"] for column in columns}
    assert names == STORED_COLUMNS
    assert not names & {"document", "filename", "path", "raw_text", "extracted_text", "findings", "matches"}


def test_the_database_row_matches_the_response(client, auth_headers, valid_payload, db_connection):
    response = client.post("/api/v1/scans", json=valid_payload, headers=auth_headers)
    body = response.get_json()
    stored = get_scan_event(db_connection, body["event_id"])
    assert stored is not None
    assert str(stored["event_id"]) == body["event_id"]
    assert body["status"] == "stored"


def test_a_database_that_cannot_be_reached_is_reported(app, auth_headers, valid_payload):
    app.config["CLOUD_DATABASE_URL"] = "postgresql://postgres:postgres@127.0.0.1:1/nope"
    response = app.test_client().post("/api/v1/scans", json=valid_payload, headers=auth_headers)
    assert response.status_code == 503
