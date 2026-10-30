"""Data passed between detection, risk, persistence and the UI.

A Candidate holds the raw match and never leaves the detection engine. A Finding is what the rest of the
application sees: it has NO raw value field — only masked_value and value_hmac (ADR-0006, NFR-01).
"""

from __future__ import annotations

from dataclasses import dataclass

from securewaste.core.detection.catalogue import Category, ReviewStatus, Severity


@dataclass(frozen=True)
class Candidate:
    rule_id: str
    category: Category
    page_number: int
    char_start: int
    char_end: int
    raw_value: str  # memory only — the engine turns this into a Finding and drops it
    confidence: float
    validation: str = ""  # e.g. "Luhn checksum passed"


@dataclass
class Finding:
    rule_id: str
    category: Category
    severity: Severity
    confidence: float
    page_number: int
    char_start: int
    char_end: int
    masked_value: str
    value_hmac: str
    context: str  # ±30 characters, every detected value inside it masked
    explanation: str
    recommendation: str
    occurrences: int = 1
    validation: str = ""
    review_status: ReviewStatus = ReviewStatus.OPEN
    id: str | None = None  # set when persisted
