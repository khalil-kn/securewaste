"""E-mail detection rule (FR-08, FR-11). Owner: Milestone 1 issue #5.

Matches a common, deliberately simple e-mail shape: local@domain.tld. The pattern uses
bounded quantifiers and word-boundary guards to avoid ReDoS (threat T-18) and to avoid
matching inside longer words.
"""

from __future__ import annotations

import re

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText

# local part (no leading/trailing word char), @, domain label(s), TLD of 2+ letters.
_EMAIL_RE = re.compile(
    r"(?<!\w)[A-Za-z0-9._%+\-]+@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?"
    r"\.[A-Za-z]{2,}(?!\w)"
)


class EmailRule(DetectionRule):
    rule_id = "email.basic"
    category = Category.EMAIL
    base_confidence = 0.8
    context_words = ("email", "e-mail", "mail", "contact")

    def find(self, page: PageText) -> list[Candidate]:
        return [
            Candidate(
                rule_id=self.rule_id,
                category=self.category,
                page_number=page.page_number,
                char_start=m.start(),
                char_end=m.end(),
                raw_value=m.group(0),
                confidence=self.base_confidence,
            )
            for m in _EMAIL_RE.finditer(page.text)
        ]
