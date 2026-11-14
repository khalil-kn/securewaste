"""SecureWaste cloud metadata API.

The cloud side receives scan metadata only: never document text, file names, paths or matched
values (ADR-0006: a raw value never leaves detection).
"""

from cloud_api.app import create_app

__all__ = ["create_app"]
