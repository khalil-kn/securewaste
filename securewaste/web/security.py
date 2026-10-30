"""Cross-cutting web security: CSRF protection, security headers and safe error pages.

Owned by the tech lead. Every route gets these protections automatically, so feature authors
cannot forget them (NFR-02, NFR-03; threats T-01, T-10, T-14 in docs/04-threat-model.md).
"""

from __future__ import annotations

import logging
import uuid

from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.exceptions import HTTPException

csrf = CSRFProtect()
log = logging.getLogger(__name__)

# 'self' only: no inline scripts, no CDNs. Put JavaScript in static/js/*.js files.
CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "frame-ancestors 'none'; form-action 'self'; base-uri 'none'; object-src 'none'"
)

ERROR_CODES = {400: "BAD_REQUEST", 404: "NOT_FOUND", 405: "BAD_REQUEST", 413: "FILE_TOO_LARGE"}


def init_app(app: Flask) -> None:
    csrf.init_app(app)  # every POST/PATCH/DELETE needs a token: form field csrf_token or header X-CSRFToken

    @app.after_request
    def set_security_headers(response):
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        # Pages showing findings must not be cached by the browser (03-api.md §1).
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return _error(400, "CSRF_INVALID", "The form expired or is missing its security token. Reload the page.")

    @app.errorhandler(HTTPException)
    def http_error(e: HTTPException):
        return _error(e.code or 500, ERROR_CODES.get(e.code, "BAD_REQUEST"), e.description)

    @app.errorhandler(Exception)
    def unexpected_error(e: Exception):
        # Log the details server-side with an ID; never show a stack trace or document content to the user.
        correlation_id = uuid.uuid4().hex[:12]
        log.exception("Unhandled error %s", correlation_id)
        return _error(500, "INTERNAL_ERROR", f"Something went wrong (reference {correlation_id}).")


def _error(status: int, code: str, message: str):
    """JSON for /api/* routes, an HTML page for everything else (03-api.md, error format)."""
    if request.path.startswith("/api/"):
        return jsonify(error={"code": code, "message": message}), status
    return render_template("error.html", status=status, code=code, message=message), status
