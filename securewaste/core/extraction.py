"""Page-aware text extraction (FR-07). Owner: Milestone 1 issue #4. Never log extracted text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from securewaste.core.upload import Limits


@dataclass(frozen=True)
class PageText:
    page_number: int  # 1-based; a TXT file is page 1
    text: str


def extract_pages(path: Path, file_type: Literal["pdf", "txt"], limits: Limits) -> list[PageText]:
    """Return one PageText per page, or raise ExtractionFailed("NO_TEXT_LAYER" | "EXTRACTION_ERROR")."""
    raise NotImplementedError("Milestone 1 issue #4")
