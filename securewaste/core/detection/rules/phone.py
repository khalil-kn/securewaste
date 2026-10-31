"""Phone number detection rule."""

from __future__ import annotations

import re

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText


class PhoneRule(DetectionRule):
    """Detect phone numbers (international and national formats)."""

    rule_id = "phone.international"
    category = Category.PHONE
    base_confidence = 0.8
    context_words = ("phone", "tel", "telephone", "mobile", "call", "contact", "number", "fax")

    # Phone regex: international format + common national formats
    # Supports: +XX XXX XXXXXXX, +XX XX XXXX XXXX, (XXX) XXX-XXXX, XXX-XXX-XXXX, etc.
    _pattern = re.compile(
        r"""
        (?<!\d)                           # Not preceded by digit
        (                                 # Capture group
            (?:                           # International format
                \+                        # Plus sign
                [1-9]\d{0,2}              # Country code (1-3 digits)
                [\s.-]?                   # Separator
                (?:\(?\d{1,4}\)?[\s.-]?){2,5}  # Number groups
            )
            |
            (?:                           # National formats
                (?:\(?\d{3}\)?[\s.-]?)    # Area code
                \d{3}[\s.-]?\d{4}         # Local number
            )
            |
            (?:                           # Simple format: 10+ digits with separators
                \d{3}[\s.-]\d{3}[\s.-]\d{4}
            )
            |
            (?:                           # 7-digit local
                \d{3}[\s.-]\d{4}
            )
        )
        (?!\d)                            # Not followed by digit
        """,
        re.VERBOSE,
    )

    def find(self, page: PageText) -> list[Candidate]:
        """Return every phone candidate on this page."""
        candidates = []
        text = page.text

        for match in self._pattern.finditer(text):
            raw_value = match.group(1)
            start, end = match.span(1)

            # Normalize: count digits
            digits = re.sub(r"\D", "", raw_value)
            if len(digits) < 7 or len(digits) > 15:
                continue  # Not a valid phone length

            confidence = self.base_confidence

            # Boost confidence for international format (starts with +)
            if raw_value.startswith("+"):
                confidence = min(0.9, confidence + 0.1)

            # Boost confidence if context words nearby
            context_start = max(0, start - 50)
            context_end = min(len(text), end + 50)
            context_window = text[context_start:context_end].lower()
            if any(word in context_window for word in self.context_words):
                confidence = min(0.95, confidence + 0.05)

            candidates.append(
                Candidate(
                    rule_id=self.rule_id,
                    category=self.category,
                    page_number=page.page_number,
                    char_start=start,
                    char_end=end,
                    raw_value=raw_value,
                    confidence=confidence,
                    validation="",
                )
            )

        return candidates