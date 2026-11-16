"""Configuration for the cloud metadata API.

Every setting comes from environment variables, so the database URL and any token never live in
the code or in the repository.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5001


@dataclass(frozen=True)
class Settings:
    """Environment-backed settings for the cloud API."""

    database_url: str
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Read the settings from the environment (or from `environ` in tests)."""
        env = os.environ if environ is None else environ
        try:
            port = int(env.get("CLOUD_API_PORT", DEFAULT_PORT))
        except ValueError as exc:
            raise ValueError(f"CLOUD_API_PORT must be an integer, got {env.get('CLOUD_API_PORT')!r}") from exc
        return cls(
            database_url=env.get("CLOUD_DATABASE_URL", "").strip(),
            host=env.get("CLOUD_API_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST,
            port=port,
        )
