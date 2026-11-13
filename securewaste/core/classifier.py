"""Document sensitivity classifier (Sprint 2: SCRUM-19/20/21).

Local-only rule-based classification. No external dependencies, no training data required.
Provides stable classification output for metadata synchronization (Sprint 3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Finding
from securewaste.core.risk import RiskAssessment


class ClassificationLabel(StrEnum):
    """Allowed classification labels for Sprint 3 metadata contract.

    These are the ONLY values that may be sent to the cloud API.
    """

    PUBLIC = "Public"
    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    HIGHLY_CONFIDENTIAL = "Highly Confidential"


class ClassifierError(Exception):
    """Raised when classification cannot be performed."""


class ClassificationError(ClassifierError):
    """Raised when the classifier cannot produce a result.

    This includes model unavailable, malformed input, or internal errors.
    Sprint 3 requirement: never send arbitrary fallback strings to the cloud API.
    Instead, the sync layer should catch this and skip synchronization.
    """


@dataclass(frozen=True)
class ClassificationResult:
    """Result of document classification."""

    label: ClassificationLabel
    """One of the four allowed labels."""

    confidence: float
    """0.0-1.0 confidence in the classification."""

    reasons: tuple[str, ...]
    """Human-readable reasons for the classification decision."""


# Classification rules thresholds
# Based on the risk scoring model (ADR-0008, Architecture §8)
_CONFIDENTIALITY_LABEL_WEIGHT = 10
_HIGH_SENSITIVITY_WEIGHT_THRESHOLD = 25  # Categories with weight >= 25 are "high-sensitivity"
_COMBINATION_BONUS = 10
_LABEL_AMPLIFIER = 10

# Score thresholds mapping to classification labels
# These align with the risk level thresholds but use classification vocabulary
_CLASSIFICATION_THRESHOLDS = [
    (75, ClassificationLabel.HIGHLY_CONFIDENTIAL),  # risk level: critical
    (25, ClassificationLabel.CONFIDENTIAL),  # risk level: medium/high boundary
    (5, ClassificationLabel.INTERNAL),  # risk level: low/informational boundary
    (0, ClassificationLabel.PUBLIC),  # risk level: informational
]


def _compute_classification_score(
    findings: list[Finding],
    risk_assessment: RiskAssessment,
) -> tuple[int, list[str]]:
    """Compute a classification score mirroring the risk scoring algorithm.

    Returns (score, reasons) where score is 0-100.
    """
    # Re-use the risk assessment's computed score and reasons
    # The risk score already incorporates all the factors we need:
    # - Category weights × confidence
    # - Diminishing repetition
    # - Combination bonus (+10 for 2+ high-sensitivity categories)
    # - Label amplifier (+10 for confidentiality label + high-sensitivity)
    # - Floors for secrets/cards
    return risk_assessment.score, list(risk_assessment.reasons)


def _score_to_label(score: int) -> ClassificationLabel:
    """Map 0-100 score to classification label."""
    for threshold, label in _CLASSIFICATION_THRESHOLDS:
        if score >= threshold:
            return label
    return ClassificationLabel.PUBLIC


def _has_confidentiality_label(findings: list[Finding]) -> bool:
    """Check if any finding is a confidentiality label (CONFIDENTIAL, INTERNAL, RESTRICTED)."""
    return any(f.category == Category.CONFIDENTIALITY_LABEL for f in findings)


def _has_high_sensitivity_finding(findings: list[Finding]) -> bool:
    """Check if any finding is from a high-sensitivity category (weight >= 25).

    High-sensitivity categories: SECRET (45), PAYMENT_CARD (40),
    NATIONAL_ID (30), PASSPORT (30), IBAN (25)
    """
    high_sensitivity_categories = {
        Category.SECRET,
        Category.PAYMENT_CARD,
        Category.NATIONAL_ID,
        Category.PASSPORT,
        Category.IBAN,
    }
    return any(f.category in high_sensitivity_categories for f in findings)


def classify_document(
    findings: list[Finding],
    risk_assessment: RiskAssessment,
) -> ClassificationResult:
    """Classify a document based on detection findings and risk assessment.

    This is the main entry point used by the scan pipeline.
    The classification is derived from the explainable risk score,
    ensuring consistency between displayed risk and synchronized metadata.

    Args:
        findings: List of detection findings from the scan
        risk_assessment: Risk assessment from the risk engine

    Returns:
        ClassificationResult with label, confidence, and reasons

    Raises:
        ClassifierError: If inputs are invalid or classification cannot be determined
    """
    if not isinstance(findings, list):
        raise ClassifierError("findings must be a list")
    if not isinstance(risk_assessment, RiskAssessment):
        raise ClassifierError("risk_assessment must be a RiskAssessment")

    # Filter out false positives (already done in risk assessment, but be safe)
    valid_findings = [f for f in findings if f.review_status != "false_positive"]

    if not valid_findings:
        # No findings = Public
        return ClassificationResult(
            label=ClassificationLabel.PUBLIC,
            confidence=1.0,
            reasons=("No sensitive data detected",),
        )

    # Compute classification score using the same algorithm as risk
    score, reasons = _compute_classification_score(valid_findings, risk_assessment)

    # Map score to label
    label = _score_to_label(score)

    # Confidence based on score distance from threshold boundaries
    # Higher confidence when further from decision boundaries
    confidence = _compute_confidence(score, label)

    return ClassificationResult(
        label=label,
        confidence=confidence,
        reasons=tuple(reasons),
    )


def _compute_confidence(score: int, label: ClassificationLabel) -> float:
    """Compute confidence based on distance from classification thresholds."""
    # Find the threshold for this label and the next one
    # _CLASSIFICATION_THRESHOLDS is [(threshold, label), ...] so we need to invert for label->threshold
    thresholds = {lbl: thresh for thresh, lbl in _CLASSIFICATION_THRESHOLDS}

    current_threshold = thresholds[label]

    # Find next higher threshold (if any)
    higher_thresholds = [t for l, t in thresholds.items() if l != label and t > current_threshold]
    next_threshold = min(higher_thresholds) if higher_thresholds else 100

    # Distance from current threshold to next threshold
    range_size = next_threshold - current_threshold

    if range_size <= 0:
        return 1.0

    # Distance from current threshold
    distance = score - current_threshold

    # Normalize: 0.5 at threshold, 1.0 at midpoint, approaching 1.0 at next threshold
    # But cap at 0.95 to reflect inherent uncertainty
    normalized = 0.5 + 0.45 * (distance / range_size)
    return min(0.95, max(0.5, normalized))


def predict_classification(text: str) -> ClassificationLabel:
    """Standalone classification from raw text (for testing/demo).

    This is the minimal contract function specified in the Sprint 3 guide.
    It runs a lightweight detection internally to produce a classification.

    Note: For production scans, use `classify_document()` with full findings
    and risk assessment for consistent results.

    Args:
        text: Document text to classify

    Returns:
        One of the four ClassificationLabel values

    Raises:
        ClassifierError: If classification cannot be performed
    """
    if not text or not text.strip():
        return ClassificationLabel.PUBLIC

    # Quick heuristic checks for common patterns
    # This mirrors the detection rules but is simplified for standalone use

    # Check for high-sensitivity patterns FIRST (highest priority)
    # These patterns mirror the detection rules but don't do full validation

    # AWS keys, API keys, secrets, private keys
    secret_pattern = re.compile(
        r"\b(AKIA[0-9A-Z]{16}|api[_-]?key\s*[:=]\s*[\"']?[a-zA-Z0-9_\-]{20,}|"
        r"secret[_-]?key\s*[:=]\s*[\"']?[a-zA-Z0-9_\-]{20,}|"
        r"password\s*[:=]\s*[\"']?[^\s\"']{8,}|"
        r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY\b)",
        re.IGNORECASE,
    )
    if secret_pattern.search(text):
        return ClassificationLabel.HIGHLY_CONFIDENTIAL

    # Payment card pattern (simplified Luhn check not done here)
    card_pattern = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")
    if card_pattern.search(text):
        return ClassificationLabel.CONFIDENTIAL

    # IBAN pattern (mod-97 check not done here)
    iban_pattern = re.compile(
        r"[A-Z]{2}\d{2}[A-Z0-9]{1,30}",
        re.IGNORECASE,
    )
    if iban_pattern.search(text):
        return ClassificationLabel.CONFIDENTIAL

    # National ID / Passport patterns (simplified)
    id_pattern = re.compile(r"\b\d{8}\b")  # 8-digit national ID
    passport_pattern = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")  # Passport-like
    if id_pattern.search(text) or passport_pattern.search(text):
        return ClassificationLabel.CONFIDENTIAL

    # Check for explicit confidentiality labels
    label_pattern = re.compile(r"(?<!\w)(CONFIDENTIAL|INTERNAL|RESTRICTED)(?!\w)")
    if label_pattern.search(text.upper()):
        return ClassificationLabel.CONFIDENTIAL

    # Email/phone/keyword patterns (lower sensitivity)
    email_pattern = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
    phone_pattern = re.compile(r"\b(?:\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b")
    if email_pattern.search(text) or phone_pattern.search(text):
        return ClassificationLabel.INTERNAL

    return ClassificationLabel.PUBLIC


def predict_classification_with_confidence(text: str) -> tuple[ClassificationLabel, float, dict[ClassificationLabel, float]]:
    """Rule-based classification with confidence scores.
    
    Args:
        text: Document text to classify
        
    Returns:
        Tuple of (label, confidence, all_probabilities)
    """
    if not text or not text.strip():
        probs = {label: 1.0 if label == ClassificationLabel.PUBLIC else 0.0 for label in ClassificationLabel}
        return ClassificationLabel.PUBLIC, 0.9, probs
    
    import re
    
    # Check for high-sensitivity patterns FIRST (highest priority)
    secret_pattern = re.compile(
        r"\b(AKIA[0-9A-Z]{16}|api[_-]?key\s*[:=]\s*[\"']?[a-zA-Z0-9_\-]{20,}|"
        r"secret[_-]?key\s*[:=]\s*[\"']?[a-zA-Z0-9_\-]{20,}|"
        r"password\s*[:=]\s*[\"']?[^\s\"']{8,}|"
        r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY\b)",
        re.IGNORECASE,
    )
    if secret_pattern.search(text):
        probs = {label: 0.9 if label == ClassificationLabel.HIGHLY_CONFIDENTIAL else 0.025 for label in ClassificationLabel}
        return ClassificationLabel.HIGHLY_CONFIDENTIAL, 0.9, probs
    
    # Payment card pattern
    card_pattern = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")
    if card_pattern.search(text):
        probs = {label: 0.85 if label == ClassificationLabel.CONFIDENTIAL else 0.05 for label in ClassificationLabel}
        return ClassificationLabel.CONFIDENTIAL, 0.85, probs
    
    # IBAN pattern
    iban_pattern = re.compile(
        r"[A-Z]{2}\d{2}[A-Z0-9]{1,30}",
        re.IGNORECASE,
    )
    if iban_pattern.search(text):
        probs = {label: 0.8 if label == ClassificationLabel.CONFIDENTIAL else 0.067 for label in ClassificationLabel}
        return ClassificationLabel.CONFIDENTIAL, 0.8, probs
    
    # National ID / Passport patterns
    id_pattern = re.compile(r"\b\d{8}\b")
    passport_pattern = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")
    if id_pattern.search(text) or passport_pattern.search(text):
        probs = {label: 0.75 if label == ClassificationLabel.CONFIDENTIAL else 0.083 for label in ClassificationLabel}
        return ClassificationLabel.CONFIDENTIAL, 0.75, probs
    
    # Check for explicit confidentiality labels
    label_pattern = re.compile(r"(?<!\w)(CONFIDENTIAL|INTERNAL|RESTRICTED)(?!\w)")
    if label_pattern.search(text.upper()):
        probs = {label: 0.7 if label == ClassificationLabel.CONFIDENTIAL else 0.1 for label in ClassificationLabel}
        return ClassificationLabel.CONFIDENTIAL, 0.7, probs
    
    # Email/phone/keyword patterns (lower sensitivity)
    email_pattern = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
    phone_pattern = re.compile(r"\b(?:\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b")
    if email_pattern.search(text) or phone_pattern.search(text):
        probs = {label: 0.65 if label == ClassificationLabel.INTERNAL else 0.117 for label in ClassificationLabel}
        return ClassificationLabel.INTERNAL, 0.65, probs
    
    # Default
    probs = {label: 1.0 if label == ClassificationLabel.PUBLIC else 0.0 for label in ClassificationLabel}
    return ClassificationLabel.PUBLIC, 0.6, probs
__all__ = [
    "ClassificationLabel",
    "ClassificationResult",
    "ClassifierError",
    "ClassificationError",
    "classify_document",
    "predict_classification",
]