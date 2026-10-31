"""Upload validation (FR-01 → FR-06). Owner: Milestone 1 issue #3.

Decide the real type from the bytes, never from the extension or the browser's MIME type.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from typing import Literal

import fitz  # PyMuPDF

from securewaste.core.errors import UploadRejected


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
    """Return metadata for a safe upload, or raise UploadRejected(code).

    Validation steps:
    1. Size check
    2. Empty check
    3. Content-type detection (magic bytes + PyMuPDF for PDF, UTF-8 for TXT)
    4. PDF-specific checks (encryption, page count, text layer)
    5. TXT-specific checks (NUL bytes)
    6. Generate safe metadata (uuid4 name, sanitized display name, SHA-256)
    """
    size = len(data)

    # 1. Size check
    if size > limits.max_bytes:
        raise UploadRejected("FILE_TOO_LARGE")

    # 2. Empty check
    if size == 0:
        raise UploadRejected("EMPTY_FILE")

    # 3. Content-type detection
    is_pdf = data.startswith(b"%PDF-")

    file_type: Literal["pdf", "txt"]
    page_count: int

    if is_pdf:
        # Try to open with PyMuPDF
        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception:
            raise UploadRejected("MALFORMED_PDF")

        try:
            # 4a. Encryption check
            if doc.is_encrypted:
                raise UploadRejected("PDF_ENCRYPTED")

            # 4b. Page count check
            page_count = doc.page_count
            if page_count > limits.max_pdf_pages:
                raise UploadRejected("TOO_MANY_PAGES")

            # 4c. Text layer check (at least one page has extractable text)
            has_text = False
            for page in doc:
                text = page.get_text()
                if text.strip():
                    has_text = True
                    break

            if not has_text:
                raise UploadRejected("NO_TEXT_LAYER")

            file_type = "pdf"
        finally:
            doc.close()
    else:
        # Try UTF-8 decode (BOM allowed)
        try:
            text = data.decode("utf-8-sig")  # handles BOM automatically
        except UnicodeDecodeError:
            raise UploadRejected("UNSUPPORTED_TYPE")

        # 5. NUL byte check
        if "\x00" in text:
            raise UploadRejected("NOT_UTF8")

        file_type = "txt"
        page_count = 1

    # 6. Generate safe metadata
    ext = "pdf" if file_type == "pdf" else "txt"
    stored_name = f"{uuid.uuid4()}.{ext}"
    display_name = _sanitize_display_name(filename)
    sha256 = hashlib.sha256(data).hexdigest()

    return ValidatedUpload(
        file_type=file_type,
        display_name=display_name,
        stored_name=stored_name,
        size_bytes=size,
        sha256=sha256,
        page_count=page_count,
    )


def _sanitize_display_name(filename: str) -> str:
    """Sanitize filename for safe display only.

    - Remove path separators and dangerous characters
    - Limit length
    - Replace unsafe chars with underscore
    """
    # Remove path components (keep only the basename)
    name = filename.replace("\\", "/").split("/")[-1]

    # Remove any remaining path separators and dangerous chars
    name = name.replace("\\", "_").replace("/", "_").replace(":", "_")

    # Replace control characters and other unsafe chars with underscore
    name = re.sub(r"[\x00-\x1f\x7f]", "_", name)

    # Limit length
    max_len = 255
    if len(name) > max_len:
        # Preserve extension if possible
        parts = name.rsplit(".", 1)
        if len(parts) == 2 and len(parts[1]) <= 10:
            base, ext = parts
            name = base[: max_len - len(ext) - 1] + "." + ext
        else:
            name = name[:max_len]

    # If empty after sanitization, provide a fallback
    if not name or name == ".":
        name = "upload"

    return name
