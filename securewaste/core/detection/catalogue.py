"""Rule catalogue: categories, weights, severities, explanations and recommendations.

This is the single source of truth shared by the detection rules (Milestone 1-2) and the risk engine
(Milestone 2). Numbers come from docs/02-architecture.md §8. Any change to a weight, threshold or text
bumps RULESET_VERSION, because every scan records the version it used (NFR-13).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

RULESET_VERSION = "2026.11.0"


class Category(StrEnum):
    SECRET = "secret"  # noqa: S105 - a category name, not a password
    PAYMENT_CARD = "payment_card"
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    IBAN = "iban"
    CONFIDENTIALITY_LABEL = "confidentiality_label"
    KEYWORD = "keyword"
    PHONE = "phone"
    EMAIL = "email"


class Severity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(StrEnum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"


# Allowed review transitions (architecture §6 state machine). The review service enforces exactly these.
REVIEW_TRANSITIONS: dict[ReviewStatus, set[ReviewStatus]] = {
    ReviewStatus.OPEN: {ReviewStatus.CONFIRMED, ReviewStatus.FALSE_POSITIVE, ReviewStatus.RESOLVED},
    ReviewStatus.CONFIRMED: {ReviewStatus.FALSE_POSITIVE, ReviewStatus.RESOLVED},
    ReviewStatus.FALSE_POSITIVE: {ReviewStatus.OPEN, ReviewStatus.CONFIRMED},
    ReviewStatus.RESOLVED: {ReviewStatus.OPEN},
}


@dataclass(frozen=True)
class CategoryInfo:
    weight: int
    severity: Severity
    label: str
    explanation: str
    recommendation: str


CATALOGUE: dict[Category, CategoryInfo] = {
    Category.SECRET: CategoryInfo(
        45,
        Severity.CRITICAL,
        "Secret / API key",
        "A credential such as an API key, token or private key gives direct access to a system.",
        "Remove it from the document and rotate the credential immediately.",
    ),
    Category.PAYMENT_CARD: CategoryInfo(
        40,
        Severity.HIGH,
        "Payment card number",
        "A number that passes the Luhn checksum is likely a real payment card number.",
        "Remove or mask the card number and follow your payment-data handling procedure.",
    ),
    Category.NATIONAL_ID: CategoryInfo(
        30,
        Severity.HIGH,
        "National ID number",
        "A national identity number found next to an identity keyword identifies a person.",
        "Remove it unless the recipient is authorised to receive identity data.",
    ),
    Category.PASSPORT: CategoryInfo(
        30,
        Severity.HIGH,
        "Passport number",
        "A passport number identifies a person and can be misused for fraud.",
        "Remove it unless the recipient is authorised to receive identity data.",
    ),
    Category.IBAN: CategoryInfo(
        25,
        Severity.HIGH,
        "IBAN",
        "A bank account number that passes the IBAN mod-97 check.",
        "Share bank details only through an approved channel; redact them otherwise.",
    ),
    Category.CONFIDENTIALITY_LABEL: CategoryInfo(
        10,
        Severity.MEDIUM,
        "Confidentiality label",
        "The document is labelled as confidential, internal or restricted.",
        "Check that the recipient is allowed to see documents with this label.",
    ),
    Category.KEYWORD: CategoryInfo(
        8,
        Severity.LOW,
        "Sensitive keyword",
        "A keyword your organisation marked as sensitive appears in the document.",
        "Review the surrounding text before sharing.",
    ),
    Category.PHONE: CategoryInfo(
        4, Severity.LOW, "Phone number", "A phone number is personal data.", "Keep it only if the recipient needs it."
    ),
    Category.EMAIL: CategoryInfo(
        3,
        Severity.LOW,
        "E-mail address",
        "An e-mail address is personal data.",
        "Keep it only if the recipient needs it.",
    ),
}

# Risk model constants (architecture §8).
MIN_CONFIDENCE_DEFAULT = 0.30
REPEAT_FACTOR = 0.2  # each extra distinct finding adds 20 % of the weight …
MAX_REPEATS = 3  # … for at most 3 extras per category
HIGH_WEIGHT = 25  # categories at or above this weight count as "high-sensitivity"
COMBINATION_BONUS = 10  # two or more high-sensitivity categories
LABEL_AMPLIFIER = 10  # confidentiality label + any high-sensitivity category
FLOOR_SECRET_HIGH_CONFIDENCE = 75
FLOOR_LUHN_CARD = 50
LEVEL_THRESHOLDS = [
    (75, Severity.CRITICAL),
    (50, Severity.HIGH),
    (25, Severity.MEDIUM),
    (10, Severity.LOW),
    (0, Severity.INFORMATIONAL),
]
CONFIDENCE_LABELS = [(0.8, "High"), (0.5, "Medium"), (0.0, "Low")]
