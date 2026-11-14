"""HTTP endpoints of the cloud metadata API."""

from __future__ import annotations

import psycopg
from flask import Blueprint, current_app, jsonify, request
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
            )
    except DuplicateEventError:
        return _error("duplicate_event", "this event_id has already been stored"), 409
    except psycopg.OperationalError:
        return _error("database_unavailable", "the database is not reachable"), 503

    return jsonify({"event_id": event.event_id, "status": "stored"}), 201


def _error(code: str, message: str):
    return jsonify({"error": code, "message": message})
