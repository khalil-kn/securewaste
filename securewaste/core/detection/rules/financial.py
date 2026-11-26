"""Payment-card and IBAN rules (FR-09, FR-10). SCRUM-46.

Both keep a candidate only when its checksum passes, so random digit runs are not reported.
Bounded quantifiers only (ReDoS, threat T-18).
"""

from __future__ import annotations

import re

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.detection.validators import iban_valid, luhn_valid
from securewaste.core.extraction import PageText

# 13–19 digits, optionally grouped by single spaces or dashes; not part of a longer number or word.
_CARD_RE = re.compile(r"(?<![\w-])\d(?:[ -]?\d){12,18}(?![\w-])")
# Country code, check digits, then 11–30 alphanumerics, optionally in groups of up to 4.
_IBAN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{2}\d{2}(?: ?[A-Z0-9]{1,4}){3,8}(?![A-Za-z0-9])")


def _candidate(rule, page, match, confidence, validation):
    return Candidate(
        rule_id=rule.rule_id,
        category=rule.category,
        page_number=page.page_number,
        char_start=match.start(),
        char_end=match.end(),
        raw_value=match.group(0),
        confidence=confidence,
        validation=validation,
    )


class PaymentCardRule(DetectionRule):
    rule_id = "payment_card.luhn"
    category = Category.PAYMENT_CARD
    base_confidence = 0.9
    context_words = ("card", "visa", "mastercard", "carte", "cvv", "expiry")

    def find(self, page: PageText) -> list[Candidate]:
        return [
            _candidate(self, page, m, self.base_confidence, "Luhn checksum passed")
            for m in _CARD_RE.finditer(page.text)
            if luhn_valid(m.group(0))
        ]


class IbanRule(DetectionRule):
    rule_id = "iban.mod97"
    category = Category.IBAN
    base_confidence = 0.95
    context_words = ("iban", "rib", "bank", "account")

    def find(self, page: PageText) -> list[Candidate]:
        return [
            _candidate(self, page, m, self.base_confidence, "IBAN mod-97 check passed")
            for m in _IBAN_RE.finditer(page.text)
            if iban_valid(m.group(0))
        ]
