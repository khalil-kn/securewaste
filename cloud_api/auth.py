"""Bearer token guard for the cloud API.

The tokens and their roles come from the environment, so no secret lives in the repository.
SCRUM-29 hardens this module; the routes only call `require_writer`.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from flask import current_app, jsonify, request

# Roles that may store scan events. Every other role is refused with 403.
WRITE_ROLES = frozenset({"employee", "admin", "security_officer"})


def parse_tokens(raw: str | None) -> dict[str, str]:
    """Read a `token:role, token:role` list into a mapping of token to role."""
    tokens: dict[str, str] = {}
    for entry in (raw or "").split(","):
        token, separator, role = entry.strip().partition(":")
        if separator and token and role:
            tokens[token] = role
    return tokens


def require_writer[View: Callable[..., Any]](view: View) -> View:
    """Refuse the request unless it carries a token of a role that may store scan events."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        header = request.headers.get("Authorization", "")
        scheme, separator, token = header.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token.strip():
            return _unauthorized("a bearer token is required")
        role = current_app.config.get("CLOUD_API_TOKENS", {}).get(token.strip())
        if role is None:
            return _unauthorized("the bearer token is not known")
        if role not in WRITE_ROLES:
            return _forbidden("this role may not store scan events")
        return view(*args, **kwargs)

    return cast("View", wrapper)


def _unauthorized(message: str):
    return jsonify({"error": "unauthorized", "message": message}), 401, {"WWW-Authenticate": "Bearer"}


def _forbidden(message: str):
    return jsonify({"error": "forbidden", "message": message}), 403


def tokens_from_env() -> dict[str, str]:
    """Read the token list from `CLOUD_API_TOKENS`."""
    return parse_tokens(os.environ.get("CLOUD_API_TOKENS"))
