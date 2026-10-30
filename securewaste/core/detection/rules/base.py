"""Base class every detection rule inherits from. Keep rules small: pattern + optional validator + context."""

from __future__ import annotations

from abc import ABC, abstractmethod

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.extraction import PageText


class DetectionRule(ABC):
    rule_id: str  # e.g. "email.basic", "payment_card.luhn"
    category: Category
    base_confidence: float
    context_words: tuple[str, ...] = ()

    @abstractmethod
    def find(self, page: PageText) -> list[Candidate]:
        """Return every candidate on this page. Use bounded regex quantifiers (ReDoS, threat T-18)."""
