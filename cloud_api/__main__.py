"""Run the cloud API: `python -m cloud_api`."""

from __future__ import annotations

from cloud_api.app import create_app
from cloud_api.config import Settings


def main() -> None:
    """Start the API on the configured host and port."""
    settings = Settings.from_env()
    if not settings.database_url:
        raise SystemExit("CLOUD_DATABASE_URL is not set")
    create_app(settings).run(host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
