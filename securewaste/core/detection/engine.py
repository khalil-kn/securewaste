"""Detection engine (FR-08 → FR-13). Owner: Milestone 1 issue #5.

The engine runs every rule on every page, drops candidates below the confidence floor, masks
each value (so the real value never leaves detection), merges duplicates of the same detected
value on the same page, and returns a list of Finding objects.

Masking is applied to the whole page text up front, so every context window is guaranteed to
hide every detected value — not just the finding's own value (ST-01 / ST-02).

Two details keep that guarantee honest:
  * Masking changes the text length ("alice.secret@example.com" -> "a•••@e•••.com"), so the
    finding's original offsets are translated into masked-text coordinates before cutting the
    window. Cutting with the original offsets shifted the window and cut words in half.
  * The window is also scrubbed for anything that LOOKS sensitive (e-mail, phone-like numbers)
    but that no rule detected, so an undetected value can never appear in a context box.
"""

from __future__ import annotations

from securewaste.core.detection.catalogue import CATALOGUE
from securewaste.core.detection.masking import (
    _context_window,
    _mask_page,
    _translate,
    value_hmac,
)
from securewaste.core.detection.models import Finding
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText


def mask_text(text: str, rules: list[DetectionRule]) -> str:
    """Return *text* with every value detected by *rules* replaced by its mask."""
    page = PageText(page_number=1, text=text)
    candidates = [candidate for rule in rules for candidate in rule.find(page)]
    return _mask_page(text, candidates)[0]


class DetectionEngine:
    def __init__(self, rules: list[DetectionRule], min_confidence: float, hmac_key: bytes):
        self.rules = rules
        self.min_confidence = min_confidence
        self.hmac_key = hmac_key

    def scan(self, pages: list[PageText]) -> list[Finding]:
        findings: list[Finding] = []
        by_fingerprint: dict[tuple, Finding] = {}

        for page in pages:
            candidates = [candidate for rule in self.rules for candidate in rule.find(page)]
            masked_text, mapping = _mask_page(page.text, candidates)

            for candidate in candidates:
                if candidate.confidence < self.min_confidence:
                    continue

                info = CATALOGUE[candidate.category]
                fingerprint = value_hmac(self.hmac_key, candidate.rule_id, candidate.raw_value)
                key = (candidate.rule_id, candidate.category, page.page_number, fingerprint)

                existing = by_fingerprint.get(key)
                if existing is not None:
                    existing.occurrences += 1
                    continue

                ctx_start = _translate(mapping, candidate.char_start, is_end=False)
                ctx_end = _translate(mapping, candidate.char_end, is_end=True)

                finding = Finding(
                    rule_id=candidate.rule_id,
                    category=candidate.category,
                    severity=info.severity,
                    confidence=candidate.confidence,
                    page_number=candidate.page_number,
                    char_start=candidate.char_start,
                    char_end=candidate.char_end,
                    masked_value=masked_text[ctx_start:ctx_end],
                    value_hmac=fingerprint,
                    context=_context_window(masked_text, ctx_start, ctx_end),
                    explanation=info.explanation,
                    recommendation=info.recommendation,
                    occurrences=1,
                    validation=candidate.validation,
                )
                findings.append(finding)
                by_fingerprint[key] = finding

        return findings
