"""Application factory of the cloud metadata API."""

from __future__ import annotations

from collections.abc import Mapping

from flask import Flask, jsonify

from cloud_api.auth import Credential, init_auth
from cloud_api.config import Settings
from cloud_api.routes import bp

# The body of a scan event is metadata only, so it is tiny. Anything larger is refused.
MAX_REQUEST_BYTES = 8 * 1024


def create_app(
    settings: Settings | None = None,
    credentials: Mapping[str, Credential] | None = None,
) -> Flask:
    """Build the Flask application of the cloud API.

    `credentials` (token-hash -> Credential) is meant for tests. In production leave it
    unset and the credentials are read from `CLOUD_API_CREDENTIALS` by `init_auth`,
    which fails fast on a malformed list.
    """
    settings = settings or Settings.from_env()
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
        CLOUD_DATABASE_URL=settings.database_url,
    )
    if credentials is not None:
        app.config["CLOUD_API_CREDENTIALS"] = dict(credentials)
    init_auth(app)  # must run after app.config.update, before serving requests
    app.register_blueprint(bp)

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify({"error": "payload_too_large", "message": "the request body is too large"}), 413

    return app
