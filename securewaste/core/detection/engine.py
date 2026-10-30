"""Detection engine (FR-08 → FR-13). Owner: Milestone 1 issue #5."""

from __future__ import annotations

from securewaste.core.detection.models import Finding
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText


class DetectionEngine:
    def __init__(self, rules: list[DetectionRule], min_confidence: float, hmac_key: bytes):
        self.rules = rules
        self.min_confidence = min_confidence
        self.hmac_key = hmac_key

    def scan(self, pages: list[PageText]) -> list[Finding]:
        """Run every rule on every page, drop low confidence, merge duplicates, mask values."""
        raise NotImplementedError("Milestone 1 issue #5")
