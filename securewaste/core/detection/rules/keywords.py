"""Configurable keyword detection rule."""

from __future__ import annotations

import re
from typing import ClassVar

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText


class KeywordRule(DetectionRule):
    """Detect configurable sensitive keywords."""

    rule_id = "keyword.custom"
    category = Category.KEYWORD
    base_confidence = 0.7
    context_words = ()  # Keywords are self-contextual

    # Keywords are provided at runtime via __init__
    _pattern: ClassVar[re.Pattern | None] = None
    _keywords: ClassVar[tuple[str, ...]] = ()

    def __init__(self, keywords: tuple[str, ...] = ()):
        """Initialize with custom keywords."""
        self._keywords = tuple(k.lower() for k in keywords if k.strip())
        if self._keywords:
            # Build regex with word boundaries, case-insensitive
            # Escape special regex chars in keywords
            escaped = [re.escape(k) for k in self._keywords]
            pattern_str = r"\b(?:" + "|".join(escaped) + r")\b"
            self._pattern = re.compile(pattern_str, re.IGNORECASE)
        else:
            self._pattern = None

    def find(self, page: PageText) -> list[Candidate]:
        """Return every keyword candidate on this page."""
        candidates = []

        if not self._pattern or not self._keywords:
            return candidates

        text = page.text

        for match in self._pattern.finditer(text):
            raw_value = match.group(0)
            start, end = match.span(0)

            # Confidence based on keyword sensitivity
            # Could be enhanced with per-keyword confidence
            confidence = self.base_confidence

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