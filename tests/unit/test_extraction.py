"""Unit tests for core/extraction.py extract_pages function."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from securewaste.core.extraction import PageText, extract_pages
from securewaste.core.upload import Limits
from securewaste.core.errors import ExtractionFailed


# Valid PDF with text content (same as in test_upload.py)
PDF_WITH_TEXT = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Hello PDF) Tj ET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000218 00000 n \n0000000305 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n362\n%%EOF"
)

# Multi-page PDF
MULTI_PAGE_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 4 0 R /Resources << /Font << /F1 6 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Page 1) Tj ET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 6 0 R /Resources << /Font << /F1 7 0 R >> >> >>\nendobj\n"
    b"6 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Page 2) Tj ET\nendstream\nendobj\n"
    b"7 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 8\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000218 00000 n \n0000000305 00000 n \n0000000370 00000 n \n0000000435 00000 n \ntrailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n492\n%%EOF"
)

# PDF with no text content (scanned)
PDF_NO_TEXT = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Resources << >> >>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n170\n%%EOF"
)

VALID_TXT = b"Hello, world!\nThis is a test file.\nMultiple lines."
TXT_WITH_BOM = b"\xef\xbb\xbfHello with BOM"


@pytest.fixture
def default_limits():
    return Limits(
        max_bytes=10 * 1024 * 1024,
        max_pdf_pages=100,
        max_extracted_chars=2_000_000,
    )


@pytest.fixture
def temp_pdf_with_text():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(PDF_WITH_TEXT)
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_multi_page_pdf():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(MULTI_PAGE_PDF)
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_pdf_no_text():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(PDF_NO_TEXT)
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_txt_file():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(VALID_TXT)
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_txt_bom():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(TXT_WITH_BOM)
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


class TestExtractPages:
    """Tests for extract_pages function."""

    def test_extract_pdf_single_page(self, temp_pdf_with_text, default_limits):
        """Extract text from single-page PDF."""
        pages = extract_pages(temp_pdf_with_text, "pdf", default_limits)

        assert len(pages) == 1
        assert isinstance(pages[0], PageText)
        assert pages[0].page_number == 1
        assert "Hello PDF" in pages[0].text

    def test_extract_pdf_multi_page(self, temp_multi_page_pdf, default_limits):
        """Extract text from multi-page PDF."""
        pages = extract_pages(temp_multi_page_pdf, "pdf", default_limits)

        assert len(pages) == 2
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2
        assert "Page 1" in pages[0].text
        assert "Page 2" in pages[1].text

    def test_extract_pdf_no_text_layer_raises(self, temp_pdf_no_text, default_limits):
        """PDF with no extractable text raises NO_TEXT_LAYER."""
        with pytest.raises(ExtractionFailed, match="NO_TEXT_LAYER"):
            extract_pages(temp_pdf_no_text, "pdf", default_limits)

    def test_extract_txt_single_page(self, temp_txt_file, default_limits):
        """Extract text from TXT file (single page)."""
        pages = extract_pages(temp_txt_file, "txt", default_limits)

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert "Hello, world!" in pages[0].text
        assert "Multiple lines" in pages[0].text

    def test_extract_txt_with_bom(self, temp_txt_bom, default_limits):
        """TXT file with UTF-8 BOM is handled correctly."""
        pages = extract_pages(temp_txt_bom, "txt", default_limits)

        assert len(pages) == 1
        assert "Hello with BOM" in pages[0].text
        # BOM should not appear in text
        assert "﻿" not in pages[0].text

    def test_extract_pdf_truncates_at_limit(self, temp_pdf_with_text):
        """Extraction stops at MAX_EXTRACTED_CHARS with truncation."""
        small_limit = Limits(
            max_bytes=10 * 1024 * 1024,
            max_pdf_pages=100,
            max_extracted_chars=10,  # Very small limit
        )

        pages = extract_pages(temp_pdf_with_text, "pdf", small_limit)

        # Should still return pages but truncated
        assert len(pages) >= 1
        total_chars = sum(len(p.text) for p in pages)
        assert total_chars <= small_limit.max_extracted_chars

    def test_extract_txt_truncates_at_limit(self, temp_txt_file):
        """TXT extraction stops at MAX_EXTRACTED_CHARS."""
        small_limit = Limits(
            max_bytes=10 * 1024 * 1024,
            max_pdf_pages=100,
            max_extracted_chars=5,
        )

        pages = extract_pages(temp_txt_file, "txt", small_limit)

        assert len(pages) == 1
        assert len(pages[0].text) <= 5

    def test_extract_corrupted_pdf_raises(self, default_limits):
        """Corrupted PDF raises EXTRACTION_ERROR."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4\nThis is corrupted")
            path = Path(f.name)
        try:
            with pytest.raises(ExtractionFailed, match="EXTRACTION_ERROR"):
                extract_pages(path, "pdf", default_limits)
        finally:
            path.unlink(missing_ok=True)

    def test_extract_nonexistent_file_raises(self, default_limits):
        """Non-existent file raises EXTRACTION_ERROR."""
        with pytest.raises(ExtractionFailed, match="EXTRACTION_ERROR"):
            extract_pages(Path("/nonexistent/file.pdf"), "pdf", default_limits)

    def test_extract_invalid_file_type_raises(self, temp_pdf_with_text, default_limits):
        """Invalid file_type raises EXTRACTION_ERROR."""
        with pytest.raises(ExtractionFailed, match="EXTRACTION_ERROR"):
            extract_pages(temp_pdf_with_text, "invalid", default_limits)

    def test_extract_txt_invalid_utf8_raises(self, default_limits):
        """TXT file with invalid UTF-8 raises EXTRACTION_ERROR."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"\xff\xfe\xfd")  # Invalid UTF-8
            path = Path(f.name)
        try:
            with pytest.raises(ExtractionFailed, match="EXTRACTION_ERROR"):
                extract_pages(path, "txt", default_limits)
        finally:
            path.unlink(missing_ok=True)

    def test_page_numbers_are_1_based(self, temp_multi_page_pdf, default_limits):
        """Page numbers are 1-based."""
        pages = extract_pages(temp_multi_page_pdf, "pdf", default_limits)

        assert pages[0].page_number == 1
        assert pages[1].page_number == 2

    def test_page_text_is_immutable(self, temp_pdf_with_text, default_limits):
        """PageText is a frozen dataclass (immutable)."""
        pages = extract_pages(temp_pdf_with_text, "pdf", default_limits)

        with pytest.raises(AttributeError):
            pages[0].page_number = 999
        with pytest.raises(AttributeError):
            pages[0].text = "modified"