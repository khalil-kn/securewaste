"""Configuration: every setting comes from environment variables (loaded from .env in development).

Why environment variables? Secrets never live in the code or the repository, and each teammate,
CI and a future Docker image can use different values without changing a line of Python.
The contract for every variable is in docs/03-api.md §4.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_SECRETS = ("SECUREWASTE_SECRET_KEY", "SECUREWASTE_HMAC_KEY")
PLACEHOLDER_VALUES = {"", "change-me", "change-me-too"}


class ConfigError(RuntimeError):
    """Raised at startup when the configuration is unsafe. The app must not start half-configured."""


def load_config(instance_path: str) -> dict:
    """Build the Flask config from the environment. Called once by create_app()."""
    load_dotenv()  # reads .env if present; real environment variables win

    for name in REQUIRED_SECRETS:
        if os.environ.get(name, "").strip() in PLACEHOLDER_VALUES:
            raise ConfigError(
                f"{name} is missing or still a placeholder. Copy .env.example to .env and set it with:\n"
                '  python -c "import secrets; print(secrets.token_hex(32))"'
            )

    max_upload_mb = int(os.environ.get("MAX_UPLOAD_MB", "10"))
    instance = Path(instance_path)
    return {
        "SECRET_KEY": os.environ["SECUREWASTE_SECRET_KEY"],  # Flask sessions + CSRF signing
        "HMAC_KEY": os.environ["SECUREWASTE_HMAC_KEY"].encode(),  # value_hmac only (ADR-0006)
        "MAX_CONTENT_LENGTH": max_upload_mb * 1024 * 1024,  # Flask answers 413 above this (FR-02)
        "MAX_UPLOAD_MB": max_upload_mb,
        "MAX_PDF_PAGES": int(os.environ.get("MAX_PDF_PAGES", "100")),
        "MAX_EXTRACTED_CHARS": int(os.environ.get("MAX_EXTRACTED_CHARS", "2000000")),
        "MIN_CONFIDENCE": float(os.environ.get("MIN_CONFIDENCE", "0.30")),
        "STORAGE_DIR": Path(os.environ.get("STORAGE_DIR", instance / "storage")),
        "DATABASE_PATH": Path(os.environ.get("DATABASE_PATH", instance / "securewaste.db")),
        "KEYWORDS": [k.strip() for k in os.environ.get("SECUREWASTE_KEYWORDS", "").split(",") if k.strip()],
        # Cookie hardening (NFR-02). SESSION_COOKIE_SECURE stays off: the MVP runs on plain HTTP localhost.
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
    }
