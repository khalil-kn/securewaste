"""Tests of the request validation, without any database."""

from __future__ import annotations

import pytest

from cloud_api.validation import PayloadError, parse_scan_payload


def test_a_complete_payload_is_accepted(valid_payload):
    event = parse_scan_payload(valid_payload)
    assert event.event_id == valid_payload["event_id"]
    assert event.event_timestamp.isoformat() == "2026-11-20T10:30:00+00:00"
    assert event.classification == "Confidential"
    assert event.risk == "High"
    assert event.counts == {"email": 2, "phone": 1, "keyword": 3}


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"event_id": "not-a-uuid"}, "event_id"),
        ({"timestamp": "2026-11-20"}, "timestamp"),
        ({"timestamp": "2026-11-20T10:30:00"}, "timestamp"),
        ({"timestamp": "20/11/2026"}, "timestamp"),
        ({"classification": "Secret"}, "classification"),
        ({"classification": "public"}, "classification"),
        ({"risk": "Critical"}, "risk"),
        ({"risk": "high"}, "risk"),
        ({"counts": {"email": 1}}, "counts"),
        ({"counts": {"email": 1, "phone": 1, "keyword": 1, "ssn": 1}}, "counts"),
        ({"counts": {"email": -1, "phone": 1, "keyword": 1}}, "counts"),
        ({"counts": {"email": 1.5, "phone": 1, "keyword": 1}}, "counts"),
        ({"counts": {"email": True, "phone": 1, "keyword": 1}}, "counts"),
        ({"counts": {"email": 10**9, "phone": 1, "keyword": 1}}, "counts"),
        ({"raw_text": "secret"}, "raw_text"),
        ({"filename": "report.pdf"}, "filename"),
    ],
)
def test_an_invalid_payload_is_refused(valid_payload, change, expected):
    payload = {**valid_payload, **change}
    with pytest.raises(PayloadError) as raised:
        parse_scan_payload(payload)
    assert any(expected in detail for detail in raised.value.details)


@pytest.mark.parametrize("field", ["event_id", "timestamp", "classification", "risk", "counts"])
def test_a_missing_field_is_refused(valid_payload, field):
    payload = {key: value for key, value in valid_payload.items() if key != field}
    with pytest.raises(PayloadError):
        parse_scan_payload(payload)


@pytest.mark.parametrize("body", [[], "scan", 3, None, True])
def test_a_body_that_is_not_an_object_is_refused(body):
    with pytest.raises(PayloadError):
        parse_scan_payload(body)
