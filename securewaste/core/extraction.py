"""Page-aware text extraction (FR-07). Owner: Milestone 1 issue #4. Never log extracted text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF

from securewaste.core.upload import Limits
from securewaste.core.errors import ExtractionFailed


@dataclass(frozen=True)
class PageText:
    page_number: int  # 1-based; a TXT file is page 1
    text: str


def extract_pages(path: Path, file_type: Literal["pdf", "txt"], limits: Limits) -> list[PageText]:
    """Return one PageText per page, or raise ExtractionFailed("NO_TEXT_LAYER" | "EXTRACTION_ERROR").

    Args:
        path: Path to the file to extract text from
        file_type: "pdf" or "txt" as determined by validate_upload
        limits: Extraction limits (max_chars, etc.)

    Returns:
        List of PageText objects, one per page (TXT = 1 page)

    Raises:
        ExtractionFailed: With code "NO_TEXT_LAYER" or "EXTRACTION_ERROR"
    """
    if file_type == "pdf":
        return _extract_pdf_pages(path, limits)
    elif file_type == "txt":
        return _extract_txt_pages(path, limits)
    else:
        raise ExtractionFailed("EXTRACTION_ERROR")


def _extract_pdf_pages(path: Path, limits: Limits) -> list[PageText]:
    """Extract text from each page of a PDF using PyMuPDF."""
    try:
        doc = fitz.open(path)
    except Exception as e:
        raise ExtractionFailed("EXTRACTION_ERROR") from e

    try:
        pages = []
        total_chars = 0

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text("text")  # Plain text extraction

            # Check extraction character limit
            total_chars += len(text)
            if total_chars > limits.max_extracted_chars:
                # Truncate the text to stay within limit
                text = text[: limits.max_extracted_chars - (total_chars - len(text))]
                pages.append(PageText(page_number=page_num + 1, text=text))
                # Stop processing further pages
                break

            pages.append(PageText(page_number=page_num + 1, text=text))

        if not pages:
            raise ExtractionFailed("NO_TEXT_LAYER")

        return pages

    finally:
        doc.close()


def _extract_txt_pages(path: Path, limits: Limits) -> list[PageText]:
    """Extract text from a TXT file (treated as single page)."""
    try:
        # Read with UTF-8, handling BOM
        data = path.read_bytes()
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ExtractionFailed("EXTRACTION_ERROR") from e
    except Exception as e:
        raise ExtractionFailed("EXTRACTION_ERROR") from e

    # Check character limit
    if len(text) > limits.max_extracted_chars:
        text = text[: limits.max_extracted_chars]

    return [PageText(page_number=1, text=text)]
