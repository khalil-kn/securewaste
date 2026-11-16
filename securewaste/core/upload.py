"""Validate PDF and TXT uploads before storing them locally."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF


@dataclass(frozen=True)
class Limits:
    max_bytes: int
    max_pdf_pages: int
    max_extracted_chars: int


@dataclass(frozen=True)
class ValidatedUpload:
    file_type: Literal["pdf", "txt"]
    display_name: str
    stored_name: str
    size_bytes: int
    sha256: str
    page_count: int


class UploadRejected(ValueError):
    """Upload failed validation; code identifies the reason."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def validate_upload(
    filename: str,
    data: bytes,
    limits: Limits,
) -> ValidatedUpload:
    """Validate an uploaded document and return its metadata."""

    if not filename or not data:
        raise UploadRejected("FILE_EMPTY")

    if len(data) > limits.max_bytes:
        raise UploadRejected("FILE_TOO_LARGE")

    extension = Path(filename).suffix.lower()

    if extension not in {".pdf", ".txt"}:
        raise UploadRejected("INVALID_FILE_TYPE")

    page_count = 1

    if extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise UploadRejected("INVALID_FILE_TYPE")

        try:
            with fitz.open(stream=BytesIO(data).getvalue(), filetype="pdf") as pdf:
                if pdf.needs_pass:
                    raise UploadRejected("PDF_ENCRYPTED")

                page_count = len(pdf)

                if page_count == 0:
                    raise UploadRejected("PDF_INVALID")

                if page_count > limits.max_pdf_pages:
                    raise UploadRejected("PDF_TOO_MANY_PAGES")

        except UploadRejected:
            raise
        except Exception as exc:
            raise UploadRejected("PDF_INVALID") from exc

        file_type = "pdf"

    else:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UploadRejected("INVALID_FILE_TYPE") from exc

        file_type = "txt"

    safe_name = Path(filename.replace("\\", "/")).name

    return ValidatedUpload(
        file_type=file_type,
        display_name=safe_name,
        stored_name=f"{uuid.uuid4()}.{file_type}",
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        page_count=page_count,
    )
