"""HTTP endpoints of the cloud metadata API."""

from __future__ import annotations

import psycopg
from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.exceptions import BadRequest

from cloud_api.auth import require_writer
from cloud_api.db import DuplicateEventError, insert_scan_event, open_connection
from cloud_api.validation import PayloadError, parse_scan_payload

bp = Blueprint("cloud_api", __name__)


@bp.get("/health")
def health():
    """Public liveness check."""
    return jsonify({"status": "ok", "service": "securewaste-cloud"})


@bp.post("/api/v1/scans")
@require_writer
def store_scan():
    """Store the metadata of one scan event."""
    if not request.is_json:
        return _error("unsupported_media_type", "the Content-Type must be application/json"), 415

    try:
        payload = request.get_json()
    except BadRequest:
        return _error("invalid_json", "the request body is not valid JSON"), 400
    if payload is None:
        return _error("invalid_json", "the request body is not valid JSON"), 400

    try:
        event = parse_scan_payload(payload)
    except PayloadError as exc:
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message": "the scan metadata does not match the contract",
                    "details": exc.details,
                }
            ),
            400,
        )

    try:
        with open_connection(current_app.config["CLOUD_DATABASE_URL"]) as connection:
            insert_scan_event(
                connection,
                event_id=event.event_id,
                event_timestamp=event.event_timestamp,
                classification=event.classification,
                risk=event.risk,
                email_count=event.counts["email"],
                phone_count=event.counts["phone"],
                keyword_count=event.counts["keyword"],
                employee_id=g.get("employee_id"),
            )
    except DuplicateEventError:
        return _error("duplicate_event", "this event_id has already been stored"), 409
    except psycopg.OperationalError:
        return _error("database_unavailable", "the database is not reachable"), 503

    return jsonify({"event_id": event.event_id, "status": "stored"}), 201


@bp.get("/api/v1/scans/<event_id>")
@require_writer
def get_scan(event_id: str):
    """Read one stored scan event, subject to owner-scoped visibility."""
    import uuid as _uuid

    try:
        _uuid.UUID(event_id)
    except ValueError:
        return _error("not_found", "the scan event was not found"), 404

    try:
        with open_connection(current_app.config["CLOUD_DATABASE_URL"]) as connection:
            row = connection.execute(
                """
                SELECT event_id, event_timestamp, classification, risk, employee_id,
                       email_count, phone_count, keyword_count, received_at
                FROM scan_events
                WHERE event_id = %s
                """,
                (event_id,),
            ).fetchone()
    except psycopg.OperationalError:
        return _error("database_unavailable", "the database is not reachable"), 503

    if row is None:
        return _error("not_found", "the scan event was not found"), 404

    role = g.get("role")
    current_employee = g.get("employee_id")
    owner = row.get("employee_id")
    owner_str = str(owner) if owner is not None else None
    if role not in {"admin", "security_officer"} and owner_str != current_employee:
        return _error("forbidden", "you may not read this scan event"), 403

    return jsonify(
        {
            "event_id": str(row["event_id"]),
            "timestamp": row["event_timestamp"].isoformat(),
            "classification": row["classification"],
            "risk": row["risk"],
            "employee_id": str(owner) if owner is not None else None,
            "counts": {
                "email": row["email_count"],
                "phone": row["phone_count"],
                "keyword": row["keyword_count"],
            },
            "received_at": row["received_at"].isoformat() if row["received_at"] is not None else None,
        }
    ), 200


def _error(code: str, message: str):
    return jsonify({"error": code, "message": message})
