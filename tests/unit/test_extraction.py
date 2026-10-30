"""Issue #4 acceptance tests: synthetic PDF/TXT extraction."""

from pathlib import Path

import pymupdf
import pytest

from securewaste.core.errors import ExtractionFailed
from securewaste.core.extraction import PageText, extract_pages
from securewaste.core.upload import Limits

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
LIMITS = Limits(max_bytes=10 * 1024 * 1024, max_pdf_pages=100, max_extracted_chars=100_000)


@pytest.fixture(scope="module", autouse=True)
def generated_documents():
    from scripts.make_fixtures import make_fixtures

    make_fixtures()


def test_three_page_invoice():
    pages = extract_pages(FIXTURES / "three_page_invoice.pdf", "pdf", LIMITS)
    assert len(pages) == 3
    assert [page.page_number for page in pages] == [1, 2, 3]
    assert all(isinstance(page, PageText) for page in pages)
    assert "SW-001" in pages[0].text
    assert "900 TND" in pages[1].text
    assert "Salary" in pages[2].text


def test_txt_is_one_page():
    pages = extract_pages(FIXTURES / "sample_records.txt", "txt", LIMITS)
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "jamie@example.invalid" in pages[0].text
    assert "Salary" in pages[0].text


def test_no_text_layer():
    with pytest.raises(ExtractionFailed) as error:
        extract_pages(FIXTURES / "image_only.pdf", "pdf", LIMITS)
    assert error.value.code == "NO_TEXT_LAYER"


def test_blank_page_retained_when_other_page_has_text(tmp_path):
    path = tmp_path / "mixed.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.new_page().insert_text((50, 50), "Second page")
        pdf.save(path)
    pages = extract_pages(path, "pdf", LIMITS)
    assert len(pages) == 2
    assert pages[0].text == ""
    assert "Second page" in pages[1].text


def test_maximum_extracted_characters(tmp_path):
    path = tmp_path / "test.txt"
    path.write_text("abcdefghij", encoding="utf-8")
    limits = Limits(max_bytes=100, max_pdf_pages=100, max_extracted_chars=5)
    with pytest.raises(ExtractionFailed) as error:
        extract_pages(path, "txt", limits)
    assert error.value.code == "EXTRACTION_ERROR"


def test_invalid_pdf(tmp_path):
    path = tmp_path / "invalid.pdf"
    path.write_bytes(b"not a pdf")
    with pytest.raises(ExtractionFailed) as error:
        extract_pages(path, "pdf", LIMITS)
    assert error.value.code == "EXTRACTION_ERROR"
