"""Tests of the scan endpoint contract."""

from __future__ import annotations


def test_a_valid_scan_is_stored(client, auth_headers, valid_payload):
    response = client.post("/api/v1/scans", json=valid_payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.get_json() == {"event_id": valid_payload["event_id"], "status": "stored"}


def test_the_same_event_twice_is_a_conflict(client, auth_headers, valid_payload):
    first = client.post("/api/v1/scans", json=valid_payload, headers=auth_headers)
    second = client.post("/api/v1/scans", json=valid_payload, headers=auth_headers)
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.get_json()["error"] == "duplicate_event"


def test_an_invalid_scan_is_refused(client, auth_headers, valid_payload):
    response = client.post(
        "/api/v1/scans",
        json={**valid_payload, "classification": "Secret"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "invalid_request"
    assert body["details"]


def test_a_body_that_is_not_json_is_refused(client, auth_headers):
    response = client.post("/api/v1/scans", data="event_id=x", headers=auth_headers)
    assert response.status_code == 415


def test_a_malformed_json_body_is_refused(client, auth_headers):
    response = client.post(
        "/api/v1/scans",
        data="{not json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_an_oversized_body_is_refused(client, auth_headers, valid_payload):
    response = client.post(
        "/api/v1/scans",
        json={**valid_payload, "padding": "x" * 9000},
        headers=auth_headers,
    )
    assert response.status_code == 413
