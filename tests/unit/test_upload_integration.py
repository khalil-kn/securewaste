
"""Tests for Secure Waste upload validation and Flask integration."""

import hashlib
import re
import uuid
from io import BytesIO

import fitz
import pytest

from securewaste.core.upload import (
    Limits,
    UploadRejected,
    validate_upload,
)


@pytest.fixture
def limits():
    return Limits(
        max_bytes=10 * 1024 * 1024,
        max_pdf_pages=100,
        max_extracted_chars=2_000_000,
    )


# --------------------------------------------------
# Upload validation tests
# --------------------------------------------------

def test_valid_txt(limits):
    data = b"Hello Secure Waste!"

    result = validate_upload("document.txt", data, limits)

    assert result.file_type == "txt"
    assert result.page_count == 1
    assert result.size_bytes == len(data)
    assert result.sha256 == hashlib.sha256(data).hexdigest()
    assert result.stored_name.endswith(".txt")

    uuid.UUID(result.stored_name.removesuffix(".txt"))


def test_valid_pdf(limits):
    pdf = fitz.open()
    pdf.new_page()
    data = pdf.tobytes()
    pdf.close()

    result = validate_upload("document.pdf", data, limits)

    assert result.file_type == "pdf"
    assert result.page_count == 1
    assert result.stored_name.endswith(".pdf")


def test_empty_file(limits):
    with pytest.raises(UploadRejected, match="FILE_EMPTY"):
        validate_upload("empty.txt", b"", limits)


def test_file_too_large(limits):
    data = b"A" * (limits.max_bytes + 1)

    with pytest.raises(UploadRejected, match="FILE_TOO_LARGE"):
        validate_upload("large.txt", data, limits)


def test_invalid_pdf_signature(limits):
    with pytest.raises(UploadRejected, match="INVALID_FILE_TYPE"):
        validate_upload("fake.pdf", b"NOT A REAL PDF", limits)


def test_corrupted_pdf(limits):
    with pytest.raises(UploadRejected, match="PDF_INVALID"):
        validate_upload("corrupted.pdf", b"%PDF-invalid", limits)


def test_invalid_utf8(limits):
    with pytest.raises(UploadRejected, match="INVALID_FILE_TYPE"):
        validate_upload("invalid.txt", b"\xff\xfe", limits)


def test_unsupported_extension(limits):
    with pytest.raises(UploadRejected, match="INVALID_FILE_TYPE"):
        validate_upload("image.png", b"image content", limits)


def test_pdf_page_limit(limits):
    pdf = fitz.open()
    pdf.new_page()
    pdf.new_page()
    data = pdf.tobytes()
    pdf.close()

    strict_limits = Limits(
        max_bytes=limits.max_bytes,
        max_pdf_pages=1,
        max_extracted_chars=limits.max_extracted_chars,
    )

    with pytest.raises(
        UploadRejected,
        match="PDF_TOO_MANY_PAGES",
    ):
        validate_upload(
            "two_pages.pdf",
            data,
            strict_limits,
        )


def test_filename_is_sanitized(limits):
    result = validate_upload(
        "../../secret.txt",
        b"Test document",
        limits,
    )

    assert result.display_name == "secret.txt"
    assert "/" not in result.stored_name
    assert ".." not in result.stored_name


# --------------------------------------------------
# Flask integration tests
# --------------------------------------------------

def get_csrf_token(client):
    """Retrieve a valid CSRF token from the upload page."""

    page = client.get("/upload")

    assert page.status_code == 200

    match = re.search(
        rb'name="csrf_token"\s+value="([^"]+)"',
        page.data,
    )

    assert match is not None, "CSRF token not found"

    return match.group(1).decode("utf-8")


def test_flask_upload_success(client, app):
    """A valid TXT upload should be scanned and cleaned up."""

    csrf_token = get_csrf_token(client)

    response = client.post(
        "/documents",
        data={
            "csrf_token": csrf_token,
            "file": (
                BytesIO(b"Hello Secure Waste!"),
                "document.txt",
            ),
        },
        content_type="multipart/form-data",
    )

    # Verify successful processing and results page.
    assert response.status_code == 200
    assert b"Scan results" in response.data
    assert b"No findings detected" in response.data

    # Temporary uploaded files must be removed after scanning.
    storage_dir = app.config["STORAGE_DIR"] / "tmp"

    stored_files = list(storage_dir.glob("*.txt"))

    assert len(stored_files) == 0


def test_flask_upload_detects_sensitive_email(client, app):
    """A TXT document containing an email should produce masked findings."""

    csrf_token = get_csrf_token(client)

    sensitive_email = b"alice@example.com"

    document = (
        b"Employee contact information:\n"
        b"Email: " + sensitive_email + b"\n"
    )

    response = client.post(
        "/documents",
        data={
            "csrf_token": csrf_token,
            "file": (
                BytesIO(document),
                "employee.txt",
            ),
        },
        content_type="multipart/form-data",
    )

    # The scan should complete successfully.
    assert response.status_code == 200

    # The results page should be displayed.
    assert b"Scan results" in response.data

    # An email finding should be present.
    assert b"Email" in response.data

    # The complete sensitive email must not appear in the HTML.
    assert sensitive_email not in response.data

    # Temporary files must be deleted.
    storage_dir = app.config["STORAGE_DIR"] / "tmp"

    assert list(storage_dir.glob("*.txt")) == []
