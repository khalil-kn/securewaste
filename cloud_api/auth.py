"""Authentication and authorization for the cloud API.

Each credential binds a bearer token to exactly one (role, employee UUID, expiry).
Only SHA-256 hashes of tokens are configured, never the tokens themselves.
Ownership always comes from the server-validated credential, never from the client.

Config format (env `CLOUD_API_CREDENTIALS`, comma separated):
    <sha256_hex>:<role>:<employee_uuid>:<expires_at_epoch_seconds>
Generate entries with `scripts/issue_credential.py`.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from functools import wraps
from typing import Any, cast

from flask import Flask, current_app, g, jsonify, request
from werkzeug.exceptions import Forbidden

log = logging.getLogger(__name__)

TOKEN_PREFIX = "swt_"  # noqa: S105  (public greppable prefix, not a secret)
MAX_TOKEN_LENGTH = 256
DEFAULT_MAX_TTL_SECONDS = 90 * 24 * 3600
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_INVALID = "invalid or expired credentials"


class Role(StrEnum):
    EMPLOYEE = "employee"
    ADMIN = "admin"
    SECURITY_OFFICER = "security_officer"


class Permission(StrEnum):
    SCAN_CREATE = "scan:create"  # store a scan event owned by the caller
    SCAN_READ_OWN = "scan:read:own"
    SCAN_READ_ALL = "scan:read:all"
    AUDIT_READ = "audit:read"
    USER_ADMIN = "user:admin"


# Single source of truth for least privilege. PROPOSAL: confirm with Jawed and Nour.
ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = {
    Role.EMPLOYEE: frozenset({Permission.SCAN_CREATE, Permission.SCAN_READ_OWN}),
    Role.SECURITY_OFFICER: frozenset({Permission.SCAN_READ_OWN, Permission.SCAN_READ_ALL, Permission.AUDIT_READ}),
    Role.ADMIN: frozenset(
        {
            Permission.SCAN_CREATE,
            Permission.SCAN_READ_OWN,
            Permission.SCAN_READ_ALL,
            Permission.USER_ADMIN,
        }
    ),
}


class AuthConfigError(RuntimeError):
    """Raised at startup for a malformed credential list. Never includes secret material."""


class AuthenticationError(Exception):
    """Internal: becomes a 401."""


class AuthorizationError(Forbidden):
    """Raised by ownership helpers: becomes a 403 JSON response."""


@dataclass(frozen=True, slots=True)
class Credential:
    token_hash: str = field(repr=False)
    role: Role
    employee_id: str
    expires_at: int


@dataclass(frozen=True, slots=True)
class Principal:
    """The server-validated caller identity for the current request."""

    employee_id: str
    role: Role

    def has(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[self.role]


# --------------------------------------------------------------------------- #
# Credential creation and parsing
# --------------------------------------------------------------------------- #
def _now() -> float:
    return time.time()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_credential(
    role: Role | str, employee_id: str, ttl_seconds: int, *, now: float | None = None
) -> tuple[str, str]:
    """Return (plaintext_token, config_entry). Show the token once; store only the entry."""
    role = Role(role)
    employee = str(uuid.UUID(employee_id))
    issued = int(_now() if now is None else now)
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return token, f"{hash_token(token)}:{role.value}:{employee}:{issued + ttl_seconds}"


def parse_credentials(
    raw: str | None,
    *,
    now: float | None = None,
    max_ttl_seconds: int = DEFAULT_MAX_TTL_SECONDS,
) -> dict[str, Credential]:
    """Parse the credential list, failing fast on anything malformed.

    Already-expired entries are skipped with a warning. Entries that outlive
    `max_ttl_seconds` are rejected to force periodic rotation.
    """
    current = _now() if now is None else now
    result: dict[str, Credential] = {}
    for position, entry in enumerate((raw or "").split(","), start=1):
        entry = entry.strip()
        if not entry:
            continue
        # Error messages reference only the position, never the entry contents.
        parts = entry.split(":")
        if len(parts) != 4:
            raise AuthConfigError(f"credential #{position}: expected sha256:role:employee_uuid:expires_at")
        token_hash, role_raw, employee_raw, expires_raw = (p.strip() for p in parts)
        if not _SHA256_RE.fullmatch(token_hash):
            raise AuthConfigError(f"credential #{position}: token must be a lowercase sha256 hex digest")
        try:
            role = Role(role_raw)
        except ValueError:
            raise AuthConfigError(f"credential #{position}: unknown role") from None
        try:
            employee_id = str(uuid.UUID(employee_raw))
        except ValueError:
            raise AuthConfigError(f"credential #{position}: employee id must be a UUID") from None
        try:
            expires_at = int(expires_raw)
        except ValueError:
            raise AuthConfigError(f"credential #{position}: expiry must be epoch seconds") from None
        if expires_at > current + max_ttl_seconds:
            raise AuthConfigError(f"credential #{position}: expiry exceeds the maximum token lifetime")
        if token_hash in result:
            raise AuthConfigError(f"credential #{position}: duplicate token")
        if expires_at <= current:
            log.warning("credential #%d for an employee is expired and was skipped", position)
            continue
        result[token_hash] = Credential(token_hash, role, employee_id, expires_at)
    return result


def credentials_from_env() -> dict[str, Credential]:
    return parse_credentials(
        os.environ.get("CLOUD_API_CREDENTIALS"),
        max_ttl_seconds=int(os.environ.get("CLOUD_API_MAX_TOKEN_TTL_SECONDS", DEFAULT_MAX_TTL_SECONDS)),
    )


def init_auth(app: Flask) -> None:
    """Load credentials (fail fast) and register the 403 JSON handler. Call once in the app factory."""
    if "CLOUD_API_CREDENTIALS" not in app.config:
        app.config["CLOUD_API_CREDENTIALS"] = credentials_from_env()
    if not app.config["CLOUD_API_CREDENTIALS"]:
        log.warning("no valid credentials configured: every protected request will be refused")

    @app.errorhandler(AuthorizationError)
    def _handle_forbidden(error: AuthorizationError):  # noqa: ANN202
        return _forbidden(error.description or "forbidden")


# --------------------------------------------------------------------------- #
# Request authentication
# --------------------------------------------------------------------------- #
def authenticate_request() -> Principal:
    header = request.headers.get("Authorization", "")
    scheme, separator, token = header.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not separator or not token:
        raise AuthenticationError("a bearer token is required")
    if len(token) > MAX_TOKEN_LENGTH:
        raise AuthenticationError(_INVALID)

    presented = hash_token(token)
    match: Credential | None = None
    # Scan every entry with a constant-time compare; no early exit.
    for stored_hash, credential in current_app.config.get("CLOUD_API_CREDENTIALS", {}).items():
        if hmac.compare_digest(stored_hash, presented):
            match = credential
    if match is None or match.expires_at <= _now():
        raise AuthenticationError(_INVALID)  # same message for unknown and expired
    return Principal(employee_id=match.employee_id, role=match.role)


def require_permission[View: Callable[..., Any]](*needed: Permission) -> Callable[[View], View]:
    """Decorator: authenticate, then require ALL listed permissions (else 401/403)."""

    def decorator(view: View) -> View:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                principal = authenticate_request()
            except AuthenticationError as exc:
                log.info("auth rejected: %s", exc)
                return _unauthorized(str(exc))
            if not all(principal.has(p) for p in needed):
                log.warning("forbidden: role=%s employee=%s", principal.role, principal.employee_id)
                return _forbidden("this role may not perform this action")
            g.principal = principal
            g.employee_id = principal.employee_id  # kept for existing routes
            g.role = principal.role.value
            return view(*args, **kwargs)

        return cast("View", wrapper)

    return decorator


def require_writer[View: Callable[..., Any]](view: View) -> View:
    """Existing decorator name. Now requires SCAN_CREATE and binds the caller's identity."""
    return require_permission(Permission.SCAN_CREATE)(view)


# --------------------------------------------------------------------------- #
# Ownership helpers (call inside views protected by require_permission)
# --------------------------------------------------------------------------- #
def current_principal() -> Principal:
    principal = g.get("principal")
    if principal is None:
        raise RuntimeError("current_principal() used outside an authenticated view")
    return cast("Principal", principal)


def _canonical(value: str | None) -> str | None:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


def resolve_owner_id(client_supplied: str | None = None) -> str:
    """Owner for a new record: always the authenticated employee.

    A client-supplied employee_id is tolerated ONLY if it matches the token's identity
    (legacy clients). Any other value is refused, never trusted.
    """
    principal = current_principal()
    if client_supplied is not None and _canonical(client_supplied) != principal.employee_id:
        raise AuthorizationError("you may not act on behalf of another employee")
    return principal.employee_id


def authorize_employee_access(target_employee_id: str) -> None:
    """Allow reading an employee's data: own data, or anyone's with SCAN_READ_ALL."""
    principal = current_principal()
    if principal.has(Permission.SCAN_READ_ALL):
        return
    if principal.has(Permission.SCAN_READ_OWN) and _canonical(target_employee_id) == principal.employee_id:
        return
    raise AuthorizationError("you may not access another employee's data")


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #
_NO_STORE = {"Cache-Control": "no-store"}


def _unauthorized(message: str):
    return (
        jsonify({"error": "unauthorized", "message": message}),
        401,
        {"WWW-Authenticate": "Bearer", **_NO_STORE},
    )


def _forbidden(message: str):
    return jsonify({"error": "forbidden", "message": message}), 403, _NO_STORE
