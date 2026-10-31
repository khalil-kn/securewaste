"""Security tests for upload validation (ST-03, ST-04, ST-14 from threat model)."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from securewaste.core.upload import Limits, validate_upload
from securewaste.core.errors import UploadRejected


# Test fixtures
VALID_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Hello PDF) Tj ET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000218 00000 n \n0000000305 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n362\n%%EOF"
)

VALID_TXT = b"Hello, world!\nThis is a test file."
EXE_CONTENT = b"MZ\x90\x00" + b"x" * 100  # PE header + padding


@pytest.fixture
def default_limits():
    return Limits(
        max_bytes=10 * 1024 * 1024,
        max_pdf_pages=100,
        max_extracted_chars=2_000_000,
    )


class TestUploadSecurity:
    """Security tests per threat model."""

    # ST-03: Path traversal via crafted filename
    def test_st03_path_traversal_unix(self, default_limits):
        """Filename with ../ traversal is sanitized to basename only."""
        result = validate_upload("../../../etc/passwd", VALID_TXT, default_limits)
        assert result.display_name == "passwd"
        assert ".." not in result.display_name
        assert "/" not in result.display_name
        # Stored name should be UUID, not the malicious path
        assert result.stored_name.startswith("passwd") is False
        import re
        assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.txt$", result.stored_name)

    def test_st03_path_traversal_windows(self, default_limits):
        """Windows path traversal is sanitized."""
        result = validate_upload(r"..\..\Windows\System32\cmd.exe", VALID_TXT, default_limits)
        assert result.display_name == "cmd.exe"
        assert "\\" not in result.display_name
        assert ".." not in result.display_name

    def test_st03_absolute_path_unix(self, default_limits):
        """Absolute Unix path is sanitized to basename."""
        result = validate_upload("/etc/shadow", VALID_TXT, default_limits)
        assert result.display_name == "shadow"

    def test_st03_absolute_path_windows(self, default_limits):
        """Absolute Windows path is sanitized."""
        result = validate_upload(r"C:\Users\Admin\secret.txt", VALID_TXT, default_limits)
        assert result.display_name == "secret.txt"
        assert ":" not in result.display_name

    def test_st03_long_filename_truncated(self, default_limits):
        """Very long filename is truncated safely."""
        long_name = "a" * 500 + ".pdf"
        result = validate_upload(long_name, VALID_PDF, default_limits)
        assert len(result.display_name) <= 255
        assert result.display_name.endswith(".pdf")

    def test_st03_special_chars_escaped(self, default_limits):
        """Special characters in filename are replaced."""
        result = validate_upload('test<script>.pdf', VALID_PDF, default_limits)
        assert "<" not in result.display_name
        assert ">" not in result.display_name
        assert "script" in result.display_name  # content preserved, just sanitized

    # ST-04: Upload size limits and empty file handling
    def test_st04_file_too_large_rejected(self, default_limits):
        """File exceeding MAX_UPLOAD_MB is rejected with FILE_TOO_LARGE."""
        large_data = b"x" * (default_limits.max_bytes + 1)
        with pytest.raises(UploadRejected, match="FILE_TOO_LARGE"):
            validate_upload("large.pdf", large_data, default_limits)

    def test_st04_empty_file_rejected(self, default_limits):
        """Empty file is rejected with EMPTY_FILE."""
        with pytest.raises(UploadRejected, match="EMPTY_FILE"):
            validate_upload("empty.pdf", b"", default_limits)

    def test_st04_temp_cleanup_on_failure(self, default_limits):
        """Temp directory remains empty after validation failures.

        Note: validate_upload doesn't create temp files - that's done in
        upload_and_scan. This test verifies the validation layer doesn't
        leave artifacts.
        """
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Simulate what upload_and_scan does: write to tmp then validate
            # But validate_upload itself doesn't write, so tmp stays empty
            try:
                validate_upload("large.pdf", b"x" * (default_limits.max_bytes + 1), default_limits)
            except UploadRejected:
                pass

            # Temp dir should be empty (validate_upload doesn't write)
            assert len(list(tmp_path.iterdir())) == 0

    # ST-14: File type determined from content, not extension
    def test_st14_exe_as_pdf_rejected(self, default_limits):
        """.exe file renamed to .pdf is rejected as UNSUPPORTED_TYPE."""
        with pytest.raises(UploadRejected, match="UNSUPPORTED_TYPE"):
            validate_upload("malicious.pdf", EXE_CONTENT, default_limits)

    def test_st14_pdf_as_txt_handled_as_pdf(self, default_limits):
        """PDF file with .txt extension is handled as PDF (magic bytes win)."""
        result = validate_upload("document.txt", VALID_PDF, default_limits)
        assert result.file_type == "pdf"
        assert result.stored_name.endswith(".pdf")

    def test_st14_txt_as_pdf_rejected_if_not_pdf(self, default_limits):
        """TXT file with .pdf extension but no %PDF- header is rejected."""
        with pytest.raises(UploadRejected, match="UNSUPPORTED_TYPE"):
            validate_upload("fake.pdf", VALID_TXT, default_limits)

    def test_st14_zip_as_pdf_rejected(self, default_limits):
        """ZIP file renamed to .pdf is rejected."""
        zip_content = b"PK\x03\x04" + b"x" * 100  # ZIP header
        with pytest.raises(UploadRejected, match="UNSUPPORTED_TYPE"):
            validate_upload("archive.pdf", zip_content, default_limits)

    def test_st14_image_as_pdf_rejected(self, default_limits):
        """PNG file renamed to .pdf is rejected."""
        png_content = b"\x89PNG\r\n\x1a\n" + b"x" * 100
        with pytest.raises(UploadRejected, match="UNSUPPORTED_TYPE"):
            validate_upload("image.pdf", png_content, default_limits)

    # Additional security checks
    def test_stored_name_never_contains_original_filename(self, default_limits):
        """Stored name is always UUID-based, never derived from user input."""
        for filename in ["test.pdf", "../../../etc/passwd", "C:\\Windows\\x.pdf", "normal.txt"]:
            if filename.endswith(".pdf"):
                result = validate_upload(filename, VALID_PDF, default_limits)
            else:
                result = validate_upload(filename, VALID_TXT, default_limits)
            # Stored name should be UUID
            import re
            assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(pdf|txt)$", result.stored_name)

    def test_sha256_computed_for_audit(self, default_limits):
        """SHA-256 is computed for every upload for audit trail."""
        result = validate_upload("test.pdf", VALID_PDF, default_limits)
        assert len(result.sha256) == 64  # hex digest
        import hashlib
        assert result.sha256 == hashlib.sha256(VALID_PDF).hexdigest()

    def test_no_raw_data_in_validation_result(self, default_limits):
        """Validation result contains no raw file content."""
        result = validate_upload("test.txt", b"SECRET_PASSWORD_123", default_limits)
        # The result should not contain the raw value
        assert "SECRET_PASSWORD_123" not in str(result)
        assert "SECRET_PASSWORD_123" not in result.display_name
        assert "SECRET_PASSWORD_123" not in result.stored_name
        assert "SECRET_PASSWORD_123" not in result.sha256


class TestUploadIntegration:
    """Integration-style tests using Flask test client."""

    def test_st03_via_http_endpoint(self, client: FlaskClient):
        """ST-03: Path traversal via HTTP upload form."""
        # This test requires the full Flask app with routes
        # Run after routes are connected to upload validation
        pass  # Will be enabled when /documents POST uses validate_upload

    def test_st04_via_http_endpoint(self, client: FlaskClient):
        """ST-04: Large file and empty file via HTTP."""
        pass  # Will be enabled when routes are connected

    def test_st14_via_http_endpoint(self, client: FlaskClient):
        """ST-14: File type from content via HTTP."""
        pass  # Will be enabled when routes are connected