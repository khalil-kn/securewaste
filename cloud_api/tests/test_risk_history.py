"""Scans stored before Sprint 4 have no risk; they must stay readable (SCRUM-46 M4)."""

import pytest

SCANS = "/api/v1/scans"


@pytest.mark.parametrize("risk", [None, "Low", "Medium", "High"])
def test_scan_events_with_and_without_risk_round_trip(client, new_event, bearer, risk):
    event = new_event()
    if risk is None:
        event.pop("risk")  # what the client sends before risk is approved, and what old scans look like
    else:
        event["risk"] = risk
    created = client.post(SCANS, json=event, headers=bearer("employee_a"))
    assert created.status_code == 201
    stored = client.get(f"{SCANS}/{event['event_id']}", headers=bearer("employee_a"))
    assert stored.status_code == 200
    body = stored.get_json()
    assert body["risk"] == risk and body["classification"] == event["classification"]


def test_a_null_risk_row_is_stored_as_null_and_read_back(client, new_event, bearer, db_connection):
    event = new_event()
    event.pop("risk")
    assert client.post(SCANS, json=event, headers=bearer("employee_a")).status_code == 201
    row = db_connection.execute("SELECT risk FROM scan_events WHERE event_id = %s", (event["event_id"],)).fetchone()
    assert row["risk"] is None
    assert client.get(f"{SCANS}/{event['event_id']}", headers=bearer("employee_a")).get_json()["risk"] is None
