"""Application factory of the cloud metadata API."""

from __future__ import annotations

import os
from collections.abc import Mapping

from flask import Flask, jsonify

from cloud_api.auth import parse_employee_ids, parse_tokens
from cloud_api.config import Settings
from cloud_api.routes import bp

# The body of a scan event is metadata only, so it is tiny. Anything larger is refused.
MAX_REQUEST_BYTES = 8 * 1024


def create_app(settings: Settings | None = None, tokens: Mapping[str, str] | None = None) -> Flask:
    """Build the Flask application of the cloud API."""
    settings = settings or Settings.from_env()
    app = Flask(__name__)
    if tokens is None:
        raw = os.environ.get("CLOUD_API_TOKENS")
        token_roles = parse_tokens(raw)
        token_employees = parse_employee_ids(raw)
    else:
        token_roles = {}
        token_employees = {}
        for token, value in tokens.items():
            if isinstance(value, (tuple, list)):
                role = value[0]
                employee_id = value[1] if len(value) > 1 else None
            elif isinstance(value, dict):
                role = value.get("role")
                employee_id = value.get("employee_id")
            else:
                role = value
                employee_id = None
            if role is not None:
                token_roles[token] = role
            token_employees[token] = employee_id
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
        CLOUD_DATABASE_URL=settings.database_url,
        CLOUD_API_TOKENS=token_roles,
        CLOUD_API_TOKEN_EMPLOYEES=token_employees,
    )
    app.register_blueprint(bp)

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify({"error": "payload_too_large", "message": "the request body is too large"}), 413

    return app
