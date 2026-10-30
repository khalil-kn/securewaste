"""Sensitive keyword detection rule (FR-11). Owner: Milestone 1 issue #5.

Matches token-configured keywords (from SECUREWASTE_KEYWORDS). Each keyword is matched as a
whole word only — a keyword is never reported when it appears inside a longer word (e.g.
"password" should not fire inside "password123").
"""

from __future__ import annotations

import re

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText


class KeywordRule(DetectionRule):
    rule_id = "keyword.custom"
    category = Category.KEYWORD
    base_confidence = 0.6
    context_words: tuple[str, ...] = ()

    def __init__(self, keywords: list[str]):
        super().__init__()
        # Escape each keyword (safe for regex metacharacters) and require word boundaries so a
        # keyword never fires inside a longer word.
        self._patterns = [re.compile(rf"(?<!\w){re.escape(kw)}(?!\w)", re.IGNORECASE) for kw in keywords]

    def find(self, page: PageText) -> list[Candidate]:
        candidates = []
        for pattern in self._patterns:
            for m in pattern.finditer(page.text):
                candidates.append(
                    Candidate(
                        rule_id=self.rule_id,
                        category=self.category,
                        page_number=page.page_number,
                        char_start=m.start(),
                        char_end=m.end(),
                        raw_value=m.group(0),
                        confidence=self.base_confidence,
                    )
                )
        return candidates
