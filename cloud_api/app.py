"""Application factory of the cloud metadata API."""

from __future__ import annotations

import os
from collections.abc import Mapping

from flask import Flask, jsonify

from cloud_api.auth import parse_tokens
from cloud_api.config import Settings
from cloud_api.routes import bp

# The body of a scan event is metadata only, so it is tiny. Anything larger is refused.
MAX_REQUEST_BYTES = 8 * 1024


def create_app(settings: Settings | None = None, tokens: Mapping[str, str] | None = None) -> Flask:
    """Build the Flask application of the cloud API."""
    settings = settings or Settings.from_env()
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
        CLOUD_DATABASE_URL=settings.database_url,
        CLOUD_API_TOKENS=dict(tokens) if tokens is not None else parse_tokens(os.environ.get("CLOUD_API_TOKENS")),
    )
    app.register_blueprint(bp)

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify({"error": "payload_too_large", "message": "the request body is too large"}), 413

    return app
