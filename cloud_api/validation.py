"""Validation of the scan metadata payload.

Pure functions: no database and no Flask, so the contract can be tested on its own.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

CLASSIFICATIONS = ("Public", "Internal", "Confidential", "Highly Confidential")
RISKS = ("Low", "Medium", "High")
COUNT_KEYS = ("email", "phone", "keyword")
MAX_COUNT = 1_000_000

ALLOWED_KEYS = frozenset({"event_id", "timestamp", "classification", "risk", "counts"})


class PayloadError(ValueError):
    """Raised when the request body does not match the metadata contract."""

    def __init__(self, details: list[str]) -> None:
        super().__init__("; ".join(details))
        self.details = details


@dataclass(frozen=True)
class ScanEvent:
    """One validated scan event, ready to be stored."""

    event_id: str
    event_timestamp: datetime
    classification: str
    risk: str
    counts: dict[str, int]


def parse_scan_payload(payload: Any) -> ScanEvent:
    """Turn a decoded JSON body into a `ScanEvent`, or raise `PayloadError`.

    Only metadata is accepted. Any other key is refused, so document text, file names, paths and
    matched values cannot be stored even by accident.
    """
    if not isinstance(payload, dict):
        raise PayloadError(["the request body must be a JSON object"])

    errors: list[str] = []
    unknown = sorted(set(payload) - ALLOWED_KEYS)
    if unknown:
        errors.append(
            f"unknown key: {', '.join(unknown)}; only the keys event_id, timestamp, classification, "
            "risk and counts are accepted, document text, file names, paths and matched values are not"
        )
    missing = sorted(ALLOWED_KEYS - set(payload))
    if missing:
        errors.append(f"missing required keys: {', '.join(missing)}")

    event_id = _event_id(payload, errors)
    event_timestamp = _timestamp(payload, errors)
    classification = _choice(payload, "classification", CLASSIFICATIONS, errors)
    risk = _choice(payload, "risk", RISKS, errors)
    counts = _counts(payload, errors)

    if errors:
        raise PayloadError(errors)

    return ScanEvent(
        event_id=event_id or "",
        event_timestamp=event_timestamp or datetime.fromtimestamp(0),
        classification=classification or "",
        risk=risk or "",
        counts=counts,
    )


def _event_id(payload: dict[str, Any], errors: list[str]) -> str | None:
    if "event_id" not in payload:
        return None
    raw = payload["event_id"]
    if not isinstance(raw, str):
        errors.append("event_id must be a UUID string")
        return None
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        errors.append("event_id must be a UUID")
        return None


def _timestamp(payload: dict[str, Any], errors: list[str]) -> datetime | None:
    if "timestamp" not in payload:
        return None
    raw = payload["timestamp"]
    if not isinstance(raw, str):
        errors.append("timestamp must be an ISO 8601 date and time")
        return None
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        errors.append("timestamp must be an ISO 8601 date and time")
        return None
    if moment.tzinfo is None:
        errors.append("timestamp must include a timezone offset")
        return None
    return moment


def _choice(payload: dict[str, Any], key: str, allowed: tuple[str, ...], errors: list[str]) -> str | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{key} must be one of {', '.join(allowed)}")
        return None
    return value


def _counts(payload: dict[str, Any], errors: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    if "counts" not in payload:
        return counts
    raw = payload["counts"]
    if not isinstance(raw, dict):
        errors.append("counts must be an object with the keys email, phone and keyword")
        return counts
    unknown = sorted(set(raw) - set(COUNT_KEYS))
    if unknown:
        errors.append(f"counts accepts only the keys {', '.join(COUNT_KEYS)}")
    missing = sorted(set(COUNT_KEYS) - set(raw))
    if missing:
        errors.append(f"counts is missing the keys: {', '.join(missing)}")
    for key in COUNT_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_COUNT:
            errors.append(f"counts.{key} must be an integer between 0 and {MAX_COUNT}")
            continue
        counts[key] = value
    return counts
