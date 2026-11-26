"""Confidentiality-label rule (FR-11). SCRUM-46.

Finds explicit classification markings such as "CONFIDENTIAL" or "Classification: Restricted".
Upper-case markings and "Classification:" headers count; the ordinary word in a sentence
("keep this confidential") does not, so prose is not reported as a label.
"""

from __future__ import annotations

import re

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText

_WORDS = r"(?:STRICTLY CONFIDENTIAL|HIGHLY CONFIDENTIAL|CONFIDENTIAL|RESTRICTED|INTERNAL USE ONLY|SECRET)"
_UPPER_RE = re.compile(rf"(?<![A-Za-z]){_WORDS}(?![A-Za-z])")  # case-sensitive: markings are upper-case
_HEADER_RE = re.compile(
    r"(?i)(?:classification|sensitivity|confidentiality)\s{0,3}[:\-]\s{0,3}"
    r"((?:strictly |highly )?confidential|restricted|internal(?: use)?(?: only)?|secret)(?![a-z])"
)


class ConfidentialityLabelRule(DetectionRule):
    rule_id = "label.marking"
    category = Category.CONFIDENTIALITY_LABEL
    base_confidence = 0.9
    context_words: tuple[str, ...] = ()

    def find(self, page: PageText) -> list[Candidate]:
        spans: dict[tuple[int, int], str] = {}
        for m in _UPPER_RE.finditer(page.text):
            spans[m.span()] = m.group(0)
        for m in _HEADER_RE.finditer(page.text):
            spans[m.span(1)] = m.group(1)
        return [
            Candidate(
                rule_id=self.rule_id,
                category=self.category,
                page_number=page.page_number,
                char_start=start,
                char_end=end,
                raw_value=value,
                confidence=self.base_confidence,
            )
            for (start, end), value in sorted(spans.items())
        ]
