# pyright: reportMissingImports=false
"""Unit tests for securewaste.core.upload.validate_upload."""

from __future__ import annotations

import pytest

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    import fitz

# validate_upload raises securewaste.core.upload.UploadRejected, so import it from there.
from securewaste.core.upload import Limits, UploadRejected, validate_upload


@pytest.fixture
def default_limits():
    return Limits(max_bytes=1024 * 1024, max_pdf_pages=5, max_extracted_chars=10000)


def make_pdf(pages: int = 1, **tobytes_kwargs) -> bytes:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = doc.tobytes(**tobytes_kwargs)
    doc.close()
    return data


def rejected_code(filename, data, limits):
    with pytest.raises(UploadRejected) as exc_info:
        validate_upload(filename, data, limits)
    return exc_info.value.code


# ---- positive controls: valid files must be accepted ----------------------
def test_valid_txt_accepted(default_limits):
    result = validate_upload("notes.txt", b"Hello world", default_limits)
    assert result.display_name == "notes.txt"


def test_valid_pdf_accepted(default_limits):
    result = validate_upload("ok.pdf", make_pdf(pages=1), default_limits)
    assert result.display_name == "ok.pdf"


# ---- rejections ------------------------------------------------------------
def test_empty_upload(default_limits):
    # Real filename so the EMPTY check is what fires, not a filename check.
    assert rejected_code("empty.txt", b"", default_limits) == "FILE_EMPTY"


def test_file_too_large(default_limits):
    data = b"A" * (default_limits.max_bytes + 1)
    assert rejected_code("test.txt", data, default_limits) == "FILE_TOO_LARGE"


def test_invalid_file_type(default_limits):
    assert rejected_code("script.exe", b"MZ99999", default_limits) == "INVALID_FILE_TYPE"


def test_fake_pdf_extension(default_limits):
    code = rejected_code("malicious.pdf", b"Not a PDF file content", default_limits)
    assert code == "INVALID_FILE_TYPE"


def test_invalid_utf8_txt(default_limits):
    code = rejected_code("notes.txt", b"\xff\xfe\xfd invalid utf8 sequence", default_limits)
    assert code == "INVALID_FILE_TYPE"


def test_malformed_pdf(default_limits):
    corrupted = b"%PDF-1.4\n1 0 obj\n<< /Corrupted /Data >>\n%%EOF"
    assert rejected_code("corrupted.pdf", corrupted, default_limits) == "PDF_INVALID"


def test_encrypted_pdf(default_limits):
    encrypted = make_pdf(
        pages=1,
        encryption=getattr(fitz, "PDF_ENCRYPT_AES_256", 4),
        owner_pw="owner123",
        user_pw="user123",
    )
    assert rejected_code("secret.pdf", encrypted, default_limits) == "PDF_ENCRYPTED"


def test_pdf_exceeding_page_limit(default_limits):
    pdf = make_pdf(pages=default_limits.max_pdf_pages + 1)
    assert rejected_code("too_long.pdf", pdf, default_limits) == "PDF_TOO_MANY_PAGES"


def test_pdf_at_page_limit_is_accepted(default_limits):
    pdf = make_pdf(pages=default_limits.max_pdf_pages)
    assert validate_upload("edge.pdf", pdf, default_limits).display_name == "edge.pdf"


# ---- filename safety -------------------------------------------------------
@pytest.mark.parametrize(
    "raw",
    ["../../etc/passwd.txt", "..\\..\\windows\\passwd.txt", "/etc/passwd.txt"],
)
def test_path_traversal_sanitization(default_limits, raw):
    result = validate_upload(raw, b"Hello world", default_limits)
    assert result.display_name == "passwd.txt"


def test_upload_rejected_is_the_class_routes_catch():
    """routes_documents.py catches errors.UploadRejected; validate_upload must raise that same class."""
    from securewaste.core import errors, upload

    assert upload.UploadRejected is errors.UploadRejected
