"""Explainable risk score (FR-14 → FR-17, ADR-0008, architecture §8). Owner: Milestone 2."""

from __future__ import annotations

from dataclasses import dataclass, field

from securewaste.core.detection.catalogue import Severity
from securewaste.core.detection.models import Finding


@dataclass(frozen=True)
class RiskAssessment:
    score: int  # 0-100
    level: Severity  # informational / low / medium / high / critical
    reasons: list[str] = field(default_factory=list)  # "+38 Payment card number (Luhn-valid, high confidence)"


def assess(findings: list[Finding]) -> RiskAssessment:
    """Ignore false positives; apply weights, repetition, bonuses, floors and thresholds from the catalogue."""
    raise NotImplementedError("Milestone 2")
