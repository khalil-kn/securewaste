"""Email detection rule."""

from __future__ import annotations

import re

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText


class EmailRule(DetectionRule):
    """Detect email addresses."""

    rule_id = "email.basic"
    category = Category.EMAIL
    base_confidence = 0.9
    context_words = ("contact", "email", "mail", "e-mail", "address", "reach")

    # Email regex: standard pattern, bounded to avoid ReDoS
    # Local part: alphanumeric + . _ % + - (max 64 chars)
    # Domain: alphanumeric + . - (max 255 chars total)
    _pattern = re.compile(
        r"""
        (?<![\w.@+-])                    # Not preceded by word char, dot, @, +, -
        (                                # Capture group for the email
            [a-zA-Z0-9._%+-]{1,64}      # Local part
            @
            [a-zA-Z0-9.-]{1,255}        # Domain part
            \.[a-zA-Z]{2,}              # TLD
        )
        (?![\w.@+-])                     # Not followed by word char, dot, @, +, -
        """,
        re.VERBOSE,
    )

    def find(self, page: PageText) -> list[Candidate]:
        """Return every email candidate on this page."""
        candidates = []
        text = page.text

        for match in self._pattern.finditer(text):
            raw_value = match.group(1)
            start, end = match.span(1)

            # Basic validation: ensure domain has valid structure
            domain = raw_value.split("@")[1]
            if "." not in domain:
                continue
            if domain.startswith(".") or domain.endswith("."):
                continue
            if ".." in domain:
                continue

            confidence = self.base_confidence

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