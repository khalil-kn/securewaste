"""Page-aware text extraction (FR-07). Never log extracted text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pymupdf

from securewaste.core.errors import ExtractionFailed
from securewaste.core.upload import Limits


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


def extract_pages(path: Path, file_type: Literal["pdf", "txt"], limits: Limits) -> list[PageText]:
    """Return one result per page or raise ExtractionFailed."""
    path = Path(path)
    if file_type == "txt":
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ExtractionFailed("EXTRACTION_ERROR") from exc
        if len(text) > limits.max_extracted_chars:
            raise ExtractionFailed("EXTRACTION_ERROR")
        return [PageText(page_number=1, text=text)]

    if file_type != "pdf":
        raise ExtractionFailed("EXTRACTION_ERROR")

    try:
        with pymupdf.open(path) as document:
            if document.is_encrypted or len(document) > limits.max_pdf_pages:
                raise ExtractionFailed("EXTRACTION_ERROR")
            pages = []
            total_chars = 0
            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text")
                total_chars += len(text)
                if total_chars > limits.max_extracted_chars:
                    raise ExtractionFailed("EXTRACTION_ERROR")
                pages.append(PageText(page_number=page_number, text=text))
    except ExtractionFailed:
        raise
    except (OSError, RuntimeError, ValueError, pymupdf.FileDataError) as exc:
        raise ExtractionFailed("EXTRACTION_ERROR") from exc

    if not any(page.text.strip() for page in pages):
        raise ExtractionFailed("NO_TEXT_LAYER")
    return pages
