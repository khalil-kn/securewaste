"""Phone number detection rule (FR-08, FR-11). Owner: Milestone 1 issue #5.

Targets Tunisian formats: national 8-digit numbers (e.g. 98123456, 98 123 456) with an
optional international prefix (+216 or 00216) or a leading 0. Separators may be spaces,
dots or hyphens. Matches are validated after normalising away separators so a longer digit
run never yields a spurious finding.
"""

from __future__ import annotations

import re

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText

# Optional prefix (+216 / 00216 / 0) then exactly eight digits, each optionally followed by a
# separator, ending on a digit (no stray leading/trailing separator is captured). Word-boundary
# guards stop the match from starting inside a longer number.
_PHONE_RE = re.compile(r"(?<!\d)(?:(?:\+216|00216|0)[ .-]?)?(?:\d[ .-]?){7}\d(?!\d)")

_CONTEXT_WINDOW = 40
_CONTEXT_BOOST = 0.2


class PhoneRule(DetectionRule):
    rule_id = "phone.tn"
    category = Category.PHONE
    base_confidence = 0.5
    context_words = ("tel", "phone", "gsm", "mobile", "call")

    def find(self, page: PageText) -> list[Candidate]:
        candidates = []
        for m in _PHONE_RE.finditer(page.text):
            raw = m.group(0)
            if not _normalise_phone(raw):
                continue
            confidence = self.base_confidence
            if _has_context_word(page.text, m.start(), m.end(), self.context_words):
                confidence = round(min(1.0, confidence + _CONTEXT_BOOST), 3)
            candidates.append(
                Candidate(
                    rule_id=self.rule_id,
                    category=self.category,
                    page_number=page.page_number,
                    char_start=m.start(),
                    char_end=m.end(),
                    raw_value=raw,
                    confidence=confidence,
                )
            )
        return candidates


def _normalise_phone(raw: str) -> str:
    """Collapse separators and strip a country prefix; return a clean 8-digit number or ''."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("216") and len(digits) == 11:
        digits = digits[3:]
    elif digits.startswith("00216") and len(digits) == 12:
        digits = digits[5:]
    elif digits.startswith("0") and len(digits) == 9:
        digits = digits[1:]
    if len(digits) == 8 and digits[0] not in "01":
        return digits
    return ""


def _has_context_word(text: str, start: int, end: int, words: tuple[str, ...]) -> bool:
    lo = max(0, start - _CONTEXT_WINDOW)
    hi = min(len(text), end + _CONTEXT_WINDOW)
    snippet = text[lo:hi].lower()
    return any(word in snippet for word in words)
