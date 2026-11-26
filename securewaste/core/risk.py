"""Explainable document risk score (FR-14 -> FR-17, ADR-0008, architecture §8). SCRUM-46.

Risk answers "how dangerous is it to share this document now?". It is computed ONLY from validated
detection findings. It never reads the classification label (Public / Internal / ...): a "Public"
document that contains an API key is still high risk, and a "Confidential" one with no findings is not.

Algorithm (all numbers live in detection/catalogue.py):
  1. Ignore findings marked false_positive.
  2. Per category: first = W x highest confidence; each further DISTINCT value adds
     REPEAT_FACTOR x W x its confidence, for at most MAX_REPEATS extras. The same value repeated
     (Finding.occurrences, or the same value on several pages) adds nothing: repetition is capped.
  3. +COMBINATION_BONUS if two or more categories with W >= HIGH_WEIGHT are present.
  4. +LABEL_AMPLIFIER if a confidentiality label appears with any W >= HIGH_WEIGHT category.
  5. score = min(100, round half up(sum)).
  6. Floors: a high-confidence secret => score >= 75; a payment card => score >= 50
     (card findings only exist when the Luhn check passed).
  7. Level from LEVEL_THRESHOLDS.

Every point is a RiskFactor, so the factors always add up to the score (tested). Reasons and
recommendations are fixed catalogue text plus counts: no masked value, context, page text or path
ever appears in the output, so it is safe for the UI and for metadata sync.

This is an application-defined estimate, not a standard or compliance score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from securewaste.core.detection.catalogue import (
    CATALOGUE,
    COMBINATION_BONUS,
    CONFIDENCE_LABELS,
    FLOOR_LUHN_CARD,
    FLOOR_SECRET_HIGH_CONFIDENCE,
    HIGH_WEIGHT,
    LABEL_AMPLIFIER,
    LEVEL_THRESHOLDS,
    MAX_REPEATS,
    REPEAT_FACTOR,
    RULESET_VERSION,
    Category,
    ReviewStatus,
    Severity,
)
from securewaste.core.detection.models import Finding

# Bump when the ALGORITHM changes. Changes to weights/thresholds bump RULESET_VERSION instead.
RISK_MODEL_VERSION = "additive-1"
SCORE_VERSION = f"{RISK_MODEL_VERSION}+{RULESET_VERSION}"

HIGH_CONFIDENCE = CONFIDENCE_LABELS[0][0]  # 0.8
MANUAL_REVIEW_RECOMMENDATION = "Several high-sensitivity data types were found: require a manual review before sharing."
NO_FINDINGS_REASON = "No sensitive findings counted (findings marked false positive are excluded)."


@dataclass(frozen=True)
class RiskFactor:
    code: str  # "category:payment_card", "combination_bonus", "label_amplifier", "cap", "floor:secret", ...
    points: float  # exact contribution; sum(points) == score
    reason: str  # safe, human-readable


@dataclass(frozen=True)
class RiskAssessment:
    score: int  # 0-100
    level: Severity  # informational / low / medium / high / critical
    reasons: list[str] = field(default_factory=list)  # "+38 Payment card number (1 distinct value, high confidence)"
    factors: tuple[RiskFactor, ...] = ()
    recommendations: list[str] = field(default_factory=list)
    score_version: str = SCORE_VERSION

    def to_dict(self) -> dict:
        """JSON-safe payload for templates and reports."""
        return {
            "score": self.score,
            "level": self.level.value,
            "reasons": list(self.reasons),
            "factors": [{"code": f.code, "points": round(f.points, 2), "reason": f.reason} for f in self.factors],
            "recommendations": list(self.recommendations),
            "score_version": self.score_version,
        }


def _round_half_up(value: float) -> int:
    # Python's round() uses banker's rounding (round(24.5) == 24); a risk boundary must not depend on that.
    # The 1e-9 absorbs float noise such as 2.7 + 2.4 + ... = 96.84999999.
    return math.floor(value + 0.5 + 1e-9)


def _points(value: float) -> str:
    """Signed points with one decimal, without a useless '.0': +38, +2.7, -0.5."""
    text = f"{value:+.1f}"
    return text[:-2] if text.endswith(".0") else text


def _confidence_word(confidence: float) -> str:
    return next(word for threshold, word in CONFIDENCE_LABELS if confidence >= threshold).lower()


def level_for(score: int) -> Severity:
    return next(level for threshold, level in LEVEL_THRESHOLDS if score >= threshold)


def _distinct_confidences(findings: list[Finding]) -> list[float]:
    """Highest confidence per distinct value (value_hmac), sorted from highest to lowest."""
    best: dict[str, float] = {}
    for f in findings:
        best[f.value_hmac] = max(best.get(f.value_hmac, 0.0), f.confidence)
    return sorted(best.values(), reverse=True)


def _category_factor(category: Category, confidences: list[float]) -> RiskFactor:
    info = CATALOGUE[category]
    extras = confidences[1 : 1 + MAX_REPEATS]
    points = info.weight * confidences[0] + sum(REPEAT_FACTOR * info.weight * c for c in extras)
    n = len(confidences)
    counted = f"{n} distinct value{'s' if n != 1 else ''}"
    if n > 1 + MAX_REPEATS:
        counted += f", only {1 + MAX_REPEATS} counted"
    reason = f"{_points(points)} {info.label} ({counted}, {_confidence_word(confidences[0])} confidence)"
    return RiskFactor(f"category:{category.value}", points, reason)


def assess(findings: list[Finding]) -> RiskAssessment:
    """Score a document from its findings. Pure and deterministic: same findings -> same result."""
    counted = [f for f in findings if f.review_status != ReviewStatus.FALSE_POSITIVE]
    by_category: dict[Category, list[Finding]] = {}
    for f in counted:
        by_category.setdefault(f.category, []).append(f)

    if not by_category:
        return RiskAssessment(0, level_for(0), [NO_FINDINGS_REASON], (), [])

    # Highest weight first, so reasons and recommendations read from most to least serious.
    categories = sorted(by_category, key=lambda c: (-CATALOGUE[c].weight, c.value))
    factors = [_category_factor(c, _distinct_confidences(by_category[c])) for c in categories]

    high = [c for c in categories if CATALOGUE[c].weight >= HIGH_WEIGHT]
    if len(high) >= 2:
        factors.append(
            RiskFactor(
                "combination_bonus",
                COMBINATION_BONUS,
                f"+{COMBINATION_BONUS} Combination of {len(high)} high-sensitivity data types",
            )
        )
    if Category.CONFIDENTIALITY_LABEL in by_category and high:
        factors.append(
            RiskFactor(
                "label_amplifier",
                LABEL_AMPLIFIER,
                f"+{LABEL_AMPLIFIER} Confidentiality label together with high-sensitivity data",
            )
        )

    # Rounding, cap and floors are factors too, so sum(points) always equals the score.
    raw = sum(f.points for f in factors)
    score = _round_half_up(raw)
    if score != raw:
        factors.append(RiskFactor("rounding", score - raw, f"{_points(score - raw)} Rounded to a whole number"))
    if score > 100:
        factors.append(RiskFactor("cap", 100 - score, "Score capped at 100"))
        score = 100

    floors = []
    secrets = by_category.get(Category.SECRET, [])
    if any(f.confidence >= HIGH_CONFIDENCE for f in secrets):
        floors.append(("floor:secret", FLOOR_SECRET_HIGH_CONFIDENCE, "a high-confidence secret"))
    if Category.PAYMENT_CARD in by_category:
        floors.append(("floor:payment_card", FLOOR_LUHN_CARD, "a Luhn-valid payment card"))
    for code, floor, what in floors:  # highest floor first; later lower floors no longer apply
        if score < floor:
            factors.append(RiskFactor(code, floor - score, f"+{floor - score} Minimum score of {floor} for {what}"))
            score = floor

    recommendations = [CATALOGUE[c].recommendation for c in categories]
    if len(high) >= 2:
        recommendations.append(MANUAL_REVIEW_RECOMMENDATION)
    recommendations = list(dict.fromkeys(recommendations))  # drop duplicates, keep order

    # Show the rounding step only when it is visible at one decimal, so the listed points add up to the score.
    reasons = [f.reason for f in factors if f.code != "rounding" or abs(f.points) >= 0.05]
    return RiskAssessment(score, level_for(score), reasons, tuple(factors), recommendations)
