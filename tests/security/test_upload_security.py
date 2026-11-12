# pyright: reportMissingImports=false
import pytest
import fitz  # PyMuPDF

from securewaste.core.upload import Limits, UploadRejected, validate_upload

@pytest.fixture
def default_limits():
    return Limits(max_bytes=1024 * 1024, max_pdf_pages=5, max_extracted_chars=10000)

def test_empty_upload(default_limits):
    with pytest.raises(UploadRejected) as exc_info:
        validate_upload("", b"", default_limits)
    assert exc_info.value.code == "FILE_EMPTY"

def test_file_too_large(default_limits):
    large_data = b"A" * (default_limits.max_bytes + 1)
    with pytest.raises(UploadRejected) as exc_info:
        validate_upload("test.txt", large_data, default_limits)
    assert exc_info.value.code == "FILE_TOO_LARGE"

def test_invalid_file_type(default_limits):
    with pytest.raises(UploadRejected) as exc_info:
        validate_upload("script.exe", b"MZ99999", default_limits)
    assert exc_info.value.code == "INVALID_FILE_TYPE"

def test_fake_pdf_extension(default_limits):
    # Has .pdf extension but lacks %PDF- header
    with pytest.raises(UploadRejected) as exc_info:
        validate_upload("malicious.pdf", b"Not a PDF file content", default_limits)
    assert exc_info.value.code == "INVALID_FILE_TYPE"

def test_invalid_utf8_txt(default_limits):
    bad_bytes = b"\xff\xfe\xfd invalid utf8 sequence"
    with pytest.raises(UploadRejected) as exc_info:
        validate_upload("notes.txt", bad_bytes, default_limits)
    assert exc_info.value.code == "INVALID_FILE_TYPE"

def test_path_traversal_sanitization(default_limits):
    # Verify name sanitization strips path traversal attempts
    valid_txt = b"Hello world"
    result = validate_upload("../../etc/passwd.txt", valid_txt, default_limits)
    assert result.display_name == "passwd.txt"



def test_malformed_pdf(default_limits: Limits) -> None:
    # Starts with valid %PDF- magic header, but body is corrupted
    corrupted_pdf = b"%PDF-1.4\n1 0 obj\n<< /Corrupted /Data >>\n%%EOF"
    with pytest.raises(UploadRejected) as exc_info:
        validate_upload("corrupted.pdf", corrupted_pdf, default_limits)
    assert exc_info.value.code == "PDF_INVALID"


def test_encrypted_pdf(default_limits: Limits) -> None:
    # Generate a password-protected PDF in memory using PyMuPDF
    doc = fitz.open()
    doc.new_page()
    encrypted_bytes = doc.tobytes(
        encryption=getattr(fitz, "PDF_ENCRYPT_AES_256", 4),
        owner_pw="owner123",
        user_pw="user123",
    )
    doc.close()

    with pytest.raises(UploadRejected) as exc_info:
        validate_upload("secret.pdf", encrypted_bytes, default_limits)
    assert exc_info.value.code == "PDF_ENCRYPTED"


def test_pdf_exceeding_page_limit(default_limits: Limits) -> None:
    # Create a 6-page PDF when default_limits.max_pdf_pages is 5
    doc = fitz.open()
    for _ in range(default_limits.max_pdf_pages + 1):
        doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    with pytest.raises(UploadRejected) as exc_info:
        validate_upload("too_long.pdf", pdf_bytes, default_limits)
    assert exc_info.value.code == "PDF_TOO_MANY_PAGES"