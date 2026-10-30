"""Upload validation (FR-01 → FR-06). Owner: Milestone 1 issue #3.

Decide the real type from the bytes, never from the extension or the browser's MIME type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Limits:
    max_bytes: int
    max_pdf_pages: int
    max_extracted_chars: int


@dataclass(frozen=True)
class ValidatedUpload:
    file_type: Literal["pdf", "txt"]
    display_name: str  # sanitised, for display only — never used to build a path
    stored_name: str  # <uuid4>.<ext>
    size_bytes: int
    sha256: str
    page_count: int


def validate_upload(filename: str, data: bytes, limits: Limits) -> ValidatedUpload:
    """Return metadata for a safe upload, or raise UploadRejected(code)."""
    raise NotImplementedError("Milestone 1 issue #3")
