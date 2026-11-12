"""Detection service for /detect (Issue #5).

Consumes the page text produced by extract_pages() — the PDF→text step owned by Milestone 1
issue #4 — and runs the detection engine over those pages. This module does not read files
itself and persists nothing (persistence is Milestone 3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from securewaste.core.detection.engine import DetectionEngine
from securewaste.core.detection.rules.email import EmailRule
from securewaste.core.detection.rules.keywords import KeywordRule
from securewaste.core.detection.rules.phone import PhoneRule
from securewaste.core.extraction import PageText, extract_pages
from securewaste.core.upload import Limits


def _build_rules(keywords: list[str]):
    rules = [EmailRule(), PhoneRule()]
    if keywords:
        rules.append(KeywordRule(keywords))
    return rules


def detect_pages(
    pages: list[PageText],
    keywords: list[str],
    min_confidence: float,
    hmac_key: bytes,
) -> list:
    """Run detection over already-extracted pages; findings never contain raw values (ST-01)."""
    rules = _build_rules(keywords)
    engine = DetectionEngine(rules, min_confidence, hmac_key)
    return engine.scan(pages)


def scan_file(
    path: Path,
    file_type: Literal["pdf", "txt"],
    limits: Limits,
    keywords: list[str],
    min_confidence: float,
    hmac_key: bytes,
) -> tuple[list, list[PageText]]:
    """Extract text (reusing issue #4's extract_pages) then detect. Returns (findings, pages)."""
    pages = extract_pages(path, file_type, limits)
    return detect_pages(pages, keywords, min_confidence, hmac_key), pages
