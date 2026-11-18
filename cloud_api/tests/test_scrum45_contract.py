"""Regression tests for the SCRUM-45 metadata contract."""

import pytest

from cloud_api.db import get_scan_event


@pytest.mark.parametrize("risk_mode", ["omitted", "null"])
def test_optional_risk(client, auth_headers, valid_payload, db_connection, risk_mode):
    if risk_mode == "omitted":
        valid_payload.pop("risk")
    else:
        valid_payload["risk"] = None

    response = client.post(
        "/api/v1/scans",
        json=valid_payload,
        headers=auth_headers,
    )

    assert response.status_code == 201

    row = get_scan_event(db_connection, valid_payload["event_id"])
    assert row is not None
    assert row["risk"] is None


def test_client_cannot_supply_employee_id(client, auth_headers, valid_payload, db_connection):
    valid_payload["employee_id"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    response = client.post(
        "/api/v1/scans",
        json=valid_payload,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert get_scan_event(db_connection, valid_payload["event_id"]) is None


def test_employee_identity_is_stored(client, auth_headers, valid_payload, db_connection):
    response = client.post(
        "/api/v1/scans",
        json=valid_payload,
        headers=auth_headers,
    )

    assert response.status_code == 201

    row = get_scan_event(db_connection, valid_payload["event_id"])

    assert row is not None
    assert str(row["employee_id"]) == ("11111111-2222-3333-4444-555555555555")
