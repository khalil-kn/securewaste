"""Detection engine (FR-08 → FR-13). Owner: Milestone 1 issue #5.

The engine runs every rule on every page, drops candidates below the confidence floor, masks
each value (so the real value never leaves detection), merges duplicates of the same detected
value on the same page, and returns a list of Finding objects.

Masking is applied to the whole page text up front, so every context window is guaranteed to
hide every detected value — not just the finding's own value (ST-01 / ST-02).
"""

from __future__ import annotations

from securewaste.core.detection.catalogue import CATALOGUE
from securewaste.core.detection.masking import mask, value_hmac
from securewaste.core.detection.models import Finding
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText

_CONTEXT_MARGIN = 30


def mask_text(text: str, rules: list[DetectionRule]) -> str:
    """Return *text* with every value detected by *rules* replaced by its mask."""
    page = PageText(page_number=1, text=text)
    masked = text
    for rule in rules:
        for candidate in rule.find(page):
            masked = masked.replace(candidate.raw_value, mask(candidate.category, candidate.raw_value))
    return masked


class DetectionEngine:
    def __init__(self, rules: list[DetectionRule], min_confidence: float, hmac_key: bytes):
        self.rules = rules
        self.min_confidence = min_confidence
        self.hmac_key = hmac_key

    def scan(self, pages: list[PageText]) -> list[Finding]:
        findings: list[Finding] = []
        by_fingerprint: dict[tuple, Finding] = {}

        for page in pages:
            masked_text = mask_text(page.text, self.rules)
            for rule in self.rules:
                for candidate in rule.find(page):
                    if candidate.confidence < self.min_confidence:
                        continue

                    info = CATALOGUE[candidate.category]
                    fingerprint = value_hmac(self.hmac_key, candidate.rule_id, candidate.raw_value)
                    key = (candidate.rule_id, candidate.category, page.page_number, fingerprint)

                    existing = by_fingerprint.get(key)
                    if existing is not None:
                        existing.occurrences += 1
                        continue

                    finding = Finding(
                        rule_id=candidate.rule_id,
                        category=candidate.category,
                        severity=info.severity,
                        confidence=candidate.confidence,
                        page_number=candidate.page_number,
                        char_start=candidate.char_start,
                        char_end=candidate.char_end,
                        masked_value=mask(candidate.category, candidate.raw_value),
                        value_hmac=fingerprint,
                        context=_context_window(masked_text, candidate.char_start, candidate.char_end),
                        explanation=info.explanation,
                        recommendation=info.recommendation,
                        occurrences=1,
                        validation=candidate.validation,
                    )
                    findings.append(finding)
                    by_fingerprint[key] = finding

        return findings


def _context_window(masked_text: str, start: int, end: int) -> str:
    """A ±30-character window from the already-masked text."""
    lo = max(0, start - _CONTEXT_MARGIN)
    hi = min(len(masked_text), end + _CONTEXT_MARGIN)
    return masked_text[lo:hi]
