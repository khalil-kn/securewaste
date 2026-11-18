"""HTTP endpoints of the cloud metadata API."""

from __future__ import annotations

import uuid
from importlib import import_module

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from cloud_api.auth import (
    Permission,
    authorize_employee_access,
    require_permission,
    resolve_owner_id,
)
from cloud_api.db import DuplicateEventError, insert_scan_event, open_connection
from cloud_api.validation import PayloadError, parse_scan_payload

psycopg = import_module("psycopg")

bp = Blueprint("cloud_api", __name__)


@bp.get("/health")
def health():
    """Public liveness check."""
    return jsonify({"status": "ok", "service": "securewaste-cloud"})


@bp.post("/api/v1/scans")
@require_permission(Permission.SCAN_CREATE)
def store_scan():
    """Store the metadata of one scan event, owned by the authenticated employee."""
    if not request.is_json:
        return _error("unsupported_media_type", "the Content-Type must be application/json"), 415

    try:
        payload = request.get_json()
    except BadRequest:
        return _error("invalid_json", "the request body is not valid JSON"), 400
    if payload is None:
        return _error("invalid_json", "the request body is not valid JSON"), 400

    # Ownership comes only from the validated token. A client-supplied employee_id is a
    # forbidden field: parse_scan_payload below rejects it with 400.
    owner_id = resolve_owner_id()

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
                employee_id=owner_id,
            )
    except DuplicateEventError:
        return _error("duplicate_event", "this event_id has already been stored"), 409
    except psycopg.OperationalError:
        return _error("database_unavailable", "the database is not reachable"), 503

    return jsonify({"event_id": event.event_id, "status": "stored"}), 201


@bp.get("/api/v1/scans/<event_id>")
@require_permission(Permission.SCAN_READ_OWN)
def get_scan(event_id: str):
    """Read one stored scan event: own events, or any event with SCAN_READ_ALL."""
    try:
        uuid.UUID(event_id)
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

    owner = row.get("employee_id")
    owner_str = str(owner) if owner is not None else None
    # Raises AuthorizationError (-> 403 JSON) unless the caller owns the event or
    # holds SCAN_READ_ALL. Legacy rows with no owner are readable only with READ_ALL.
    authorize_employee_access(owner_str if owner_str is not None else "")

    return jsonify(
        {
            "event_id": str(row["event_id"]),
            "timestamp": row["event_timestamp"].isoformat(),
            "classification": row["classification"],
            "risk": row["risk"],
            "employee_id": owner_str,
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
